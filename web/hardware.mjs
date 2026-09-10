// Independent adapter for the packet layout in eun022/hand_drawing.
// Reference commit: 2fdfa07c7f61cdc5a6603c33fc8b643a2b4036fb.
export function packCells(dots, y, columns) {
    return Uint8Array.from({length:columns},(_,cell)=>{
        let bits=0;
        for(let row=0;row<4;row++) {
            if(dots[y+row]?.[cell*2]) bits|=1<<row;
            if(dots[y+row]?.[cell*2+1]) bits|=1<<(row+4);
        }
        return bits;
    });
}
export function displayPacket(line, cells) {
    const body=Uint8Array.from([line,2,0,line===0?128:0,0,...cells]);
    let check=0xa5;for(const byte of body)check^=byte;
    const length=body.length+1;
    return Uint8Array.from([0xaa,0x55,length>>8,length&255,...body,check]);
}
export function extractPackets(buffer) {
    const packets=[];let data=Array.from(buffer);
    while(data.length>=4) {
        if(data[0]!==0xaa||data[1]!==0x55){data.shift();continue;}
        const size=(data[2]<<8)+data[3]+4;
        if(size<9||size>1024){data.shift();continue;}
        if(data.length<size)break;
        const packet=data.splice(0,size);let check=0xa5;
        for(const byte of packet.slice(4,-1))check^=byte;
        if(check===packet.at(-1))packets.push(packet);
    }
    return {packets,rest:data};
}
export class SerialPad {
    constructor(onStatus,onCommand){this.onStatus=onStatus;this.onCommand=onCommand;this.previous=[];this.buffer=[];this.mask=0;this.pending=null;this.busy=false;}
    async connect(){
        if(!navigator.serial)throw new Error('Chrome 또는 Edge의 localhost에서 USB 연결을 사용하세요');
        this.port=await navigator.serial.requestPort({filters:[{usbVendorId:1027,usbProductId:24592},{usbVendorId:1027,usbProductId:24597}]});
        await this.port.open({baudRate:115200,dataBits:8});
        this.writer=this.port.writable.getWriter();this.reader=this.port.readable.getReader();this.connected=true;
        this.previous=[];this.readTask=this.read();this.onStatus('USB 연결됨 · 출력 확인 중');
    }
    async read(){
        try{
            while(this.connected){
                const {value,done}=await this.reader.read();if(done)break;
                const parsed=extractPackets([...this.buffer,...value]);this.buffer=parsed.rest;
                for(const p of parsed.packets){
                    if(p[5]===2&&p[6]===1&&this.ack&&this.ack.line===p[4]){
                        const ack=this.ack;this.ack=null;
                        p[8]===0?ack.resolve():ack.reject(new Error('패드가 출력을 거부했습니다'));
                    }
                    if(p[5]===3&&p[6]===0x32){
                        const mask=p[8]>>4;
                        for(const [bit,command] of [[8,'minimap'],[4,'scene'],[2,'resources'],[1,'pause']]){
                            if((mask&bit)&&!(this.mask&bit))this.onCommand(command);
                        }
                        this.mask=mask;
                    }
                }
            }
        }catch(error){if(this.connected)this.onStatus('USB 수신 중단: '+error.message);}
        finally{this.connected=false;this.reader.releaseLock();this.onStatus('USB 연결 해제');}
    }
    update(state){
        if(!this.connected||!state)return;
        if(state.width!==60||state.height!==40||state.time_width!==40||state.time_height!==4){this.onStatus('60×40 / 40×4 패드만 지원합니다');return;}
        this.pending=state;if(!this.busy)this.flush();
    }
    async send(line,bytes){
        let timer;
        const response=new Promise((resolve,reject)=>{
            this.ack={line,resolve,reject};
            timer=setTimeout(()=>{this.ack=null;reject(new Error('패드 응답 없음. USB 연결을 확인하세요'));},900);
        });
        // Observe the ACK immediately, including a write failure or disconnect.
        const result=response.then(()=>null,error=>error);
        try{await this.writer.write(displayPacket(line,bytes));const error=await result;if(error)throw error;}
        finally{clearTimeout(timer);this.ack=null;}
    }
    async flush(){
        this.busy=true;
        try{
            while(this.pending&&this.connected){
                const state=this.pending;this.pending=null;
                const lines=[packCells(state.time_dots,0,20),...Array.from({length:10},(_,i)=>packCells(state.dots,i*4,30))];
                for(let line=0;line<lines.length;line++){
                    const key=Array.from(lines[line]).join(',');
                    if(this.previous[line]===key)continue;
                    await this.send(line,lines[line]);this.previous[line]=key;
                }
                this.onStatus('USB 연결됨 · 패드 출력 확인됨');
            }
        }catch(error){this.pending=null;await this.disconnect(false);this.onStatus(error.message);}
        finally{this.busy=false;}
    }
    async disconnect(report=true){
        this.connected=false;this.pending=null;
        if(this.ack){this.ack.reject(new Error('USB 연결 해제'));this.ack=null;}
        try{await this.reader?.cancel();await this.readTask;}catch{}
        try{this.writer?.releaseLock();await this.port?.close();}catch{}
        this.writer=null;this.port=null;
        if(report)this.onStatus('USB 연결 해제');
    }
}
if(typeof document!=='undefined'){
    const status=document.getElementById('hardware-status');
    const pad=new SerialPad(text=>status.textContent=text,command=>window.DotduInput.command(command));
    const usb=document.getElementById('usb-button');
    usb.addEventListener('click',async()=>{
        usb.disabled=true;
        try{
            if(pad.connected)await pad.disconnect();
            else {await pad.connect();pad.update(window.DotduInput.state());}
        }catch(error){status.textContent=error.name==='NotFoundError'?'장치 선택 취소':error.message;await pad.disconnect(false);}
        finally{usb.disabled=false;usb.textContent=pad.connected?'USB 연결 해제':'USB 패드 연결';}
    });
    window.addEventListener('dotdu-state',event=>pad.update(event.detail));
    let socket=null,held=false,valid=false,lastFrame=0;
    const button=document.getElementById('tracking-button'),hold=document.getElementById('tracking-hold'),trackingStatus=document.getElementById('tracking-status');
    function stopHold(){if(held)window.DotduInput.command('scene');held=false;hold.textContent='누르기 시작';hold.setAttribute('aria-pressed','false');}
    hold.addEventListener('click',()=>{
        if(!valid){trackingStatus.textContent='손 좌표를 먼저 확인하세요';return;}
        held=!held;window.DotduInput[held?'press':'release']();hold.textContent=held?'손 떼기':'누르기 시작';hold.setAttribute('aria-pressed',String(held));
    });
    button.addEventListener('click',()=>{
        if(socket){socket.close();return;}
        try{
            const address=new URL(document.getElementById('tracking-url').value);
            if(!['ws:','wss:'].includes(address.protocol))throw new Error('ws:// 또는 wss:// 주소를 입력하세요');
            socket=new WebSocket(address.href);button.disabled=true;
            socket.onopen=()=>{button.disabled=false;button.textContent='손 추적 연결 해제';trackingStatus.textContent='연결됨 · 손 좌표 대기';};
            socket.onmessage=event=>{
                try{
                    const data=JSON.parse(event.data);if(data.type!=='frame')return;
                    const pt=data.scaled_tip;
                    valid=data.hand_detected&&Array.isArray(pt)&&pt.length===2&&pt.every(Number.isFinite)&&pt[0]>=0&&pt[0]<60&&pt[1]>=0&&pt[1]<40;
                    hold.disabled=!valid;lastFrame=Date.now();
                    if(!valid){stopHold();trackingStatus.textContent='손 좌표 없음';return;}
                    window.DotduInput.move(pt[0],pt[1]);
                    trackingStatus.textContent=`손 좌표 ${pt[0]}, ${pt[1]} · ${held?'누르는 중':'탐색 중'}`;
                }catch{trackingStatus.textContent='손 좌표 형식을 확인하세요';}
            };
            socket.onerror=()=>{trackingStatus.textContent='손 추적 서버 연결 실패';};
            socket.onclose=()=>{stopHold();valid=false;hold.disabled=true;socket=null;button.disabled=false;button.textContent='손 추적 서버 연결';trackingStatus.textContent='연결 해제';};
        }catch(error){socket=null;button.disabled=false;trackingStatus.textContent=error.message;}
    });
    setInterval(()=>{if(valid&&Date.now()-lastFrame>1500){valid=false;hold.disabled=true;stopHold();trackingStatus.textContent='손 좌표 수신 중단';}},500);
}
