/* Separate task / reward channels. Original uploaded MP3 bytes are retained. */
class GameAudio {
    constructor(options = {}) {
        this.contextFactory = options.contextFactory || (() => new (window.AudioContext || window.webkitAudioContext)());
        this.fetcher = options.fetcher || (url => fetch(url));
        this.onStatus = options.onStatus || (() => {});
        this.now = options.now || (() => performance.now());
        // Fallbacks support old configs; game_config.json overrides these via state.
        this.settings = {
            default_volume:0.7,
            work_gain:{water:0.45,soil:0.45,cut:0.8,cook:0.8},
            work_gain_during_tts:{water:0.18,soil:0.18,cut:0.32,cook:0.32},
            reward_gain:0.42,reward_gain_during_tts:0.25,
            cooking_correct_interval_ms:650,other_correct_interval_ms:90,
            click_duration_ms:650,motion_idle_ms:450,motion_check_interval_ms:120,
            correct_max_load_age_ms:650,max_reward_sources:2
        };
        this.enabled = true; this.volume = 0.7; this.ducked = false;
        this.held = false; this.work = null; this.workName = null; this.workToken = 0;
        this.buffers = new Map(); this.raw = new Map(); this.rewardSources = new Set();
        this.clickSources = new Set(); this.clickToken = 0;
        this.effectToken = 0; this.lastPosition = null; this.lastCorrectAt = -Infinity; this.lastMotion = 0;
        this.urls = Object.fromEntries(['water','soil','cut','cook','correct'].map(n => [n, `/static/audio/${n}.mp3`]));
    }
    configure(settings = {}) {
        this.settings = {
            ...this.settings, ...settings,
            work_gain:{...this.settings.work_gain,...settings.work_gain},
            work_gain_during_tts:{...this.settings.work_gain_during_tts,...settings.work_gain_during_tts}
        };
        this.setVolume(this.settings.default_volume);
        this.setDucked(this.ducked);
    }
    preload() {
        for (const [name,url] of Object.entries(this.urls)) {
            this.raw.set(name, this.fetcher(url).then(r => {
                if (!r.ok) throw new Error(`${name} 음원 로드 실패`);
                return r.arrayBuffer();
            }).catch(error => {this.onStatus(error.message);return null;}));
        }
    }
    unlock() {
        try {
            if (!this.context) {
                this.context = this.contextFactory();
                this.master = this.context.createGain(); this.master.connect(this.context.destination);
                this.workGain = this.context.createGain(); this.workGain.connect(this.master);
                this.rewardGain = this.context.createGain(); this.rewardGain.gain.value = this.settings.reward_gain; this.rewardGain.connect(this.master);
                this.setVolume(this.volume); this.setDucked(this.ducked);
            }
            if (this.context.state === 'suspended') this.context.resume().catch(() => this.onStatus('소리 버튼을 눌러 오디오를 활성화하세요'));
        } catch {this.onStatus('오디오 미지원 · 자막으로 안내합니다');}
    }
    load(name) {
        if (!this.context || !this.urls[name]) return Promise.resolve(null);
        if (!this.raw.size) this.preload();
        if (!this.buffers.has(name)) this.buffers.set(name, this.raw.get(name).then(bytes => bytes ? this.context.decodeAudioData(bytes.slice(0)) : null).catch(() => {this.onStatus(`${name} 음원 재생 불가`);return null;}));
        return this.buffers.get(name);
    }
    setVolume(value) {
        this.volume = Math.max(0,Math.min(1,Number(value)||0));
        if (this.master) this.master.gain.setTargetAtTime(this.enabled ? this.volume : 0,this.context.currentTime,0.015);
    }
    setEnabled(enabled) {
        this.enabled = !!enabled;
        if (!this.enabled) this.stopAll();
        this.setVolume(this.volume);
    }
    setDucked(ducked) {
        const workName = this.workName || 'water';
        this.ducked = !!ducked;
        if (this.workGain) this.workGain.gain.setTargetAtTime(this.ducked ? this.settings.work_gain_during_tts[workName] : this.settings.work_gain[workName],this.context.currentTime,0.03);
        if (this.rewardGain) this.rewardGain.gain.setTargetAtTime(this.ducked ? this.settings.reward_gain_during_tts : this.settings.reward_gain,this.context.currentTime,0.02);
    }
    inputDown(state, x, y) {
        this.lastPosition = [x,y];
        this.held = true; this.lastMotion = this.now(); this.unlock();
        if (state?.paused || state?.day_ended) return;
        if (state?.page === 'water_minigame') {this.clickSound('water');this.startWork('water');}
        else if (state?.page === 'fertilizer_minigame') {this.clickSound('soil');this.startWork('soil');}
    }
    async clickSound(name) {
        if (!this.enabled) return;
        const token = ++this.clickToken, effect = this.effectToken;
        for (const source of this.clickSources) {try {source.stop();} catch {}}
        this.clickSources.clear();
        const buffer = await this.load(name);
        // A normal release must not cancel a short click while MP3 decoding.
        if (!buffer || !this.enabled || token !== this.clickToken || effect !== this.effectToken) return;
        const source = this.context.createBufferSource();
        source.buffer = buffer; source.connect(this.workGain);
        this.clickSources.add(source);
        source.onended = () => {this.clickSources.delete(source);source.disconnect();};
        source.start(0, 0, Math.min(this.settings.click_duration_ms / 1000, buffer.duration));
    }
    inputUp() {this.held = false; this.stopWork();}
    move(x,y) {
        if (!this.lastPosition || Math.hypot(x-this.lastPosition[0],y-this.lastPosition[1])>0.05) this.pulse();
        this.lastPosition=[x,y];
    }
    pulse() {
        this.lastMotion = this.now();
        if (this.workGain) this.setDucked(this.ducked);
    }
    async startWork(name) {
        if (!this.enabled || !this.held || !['water','soil','cut','cook'].includes(name)) return;
        if (this.workName === name) return;
        this.stopWork();this.workName=name;
        const token=this.workToken;
        const buffer=await this.load(name);
        if (!buffer || token!==this.workToken || !this.held || !this.enabled) return;
        const source=this.context.createBufferSource();source.buffer=buffer;source.loop=true;
        source.connect(this.workGain);this.work=source;this.setDucked(this.ducked);source.start();
        source.onended=()=>source.disconnect();
        this.onStatus(({water:'물 뿌리는 중',soil:'비료 뿌리는 중',cut:'재료 자르는 중',cook:'젓는 중'})[name]);
        // Cutting/stirring only remains audible while the pointer is moving.
        this.motionTimer=setInterval(()=>{
            if (['cut','cook'].includes(this.workName) && this.now()-this.lastMotion>this.settings.motion_idle_ms)
                this.workGain.gain.setTargetAtTime(0,this.context.currentTime,0.035);
        },this.settings.motion_check_interval_ms);
    }
    stopWork() {
        const wasWorking = !!this.workName;
        this.workToken++;this.workName=null;clearInterval(this.motionTimer);
        if(wasWorking)this.onStatus(this.enabled?"작업음 · 성공음 준비":"효과음 꺼짐");
        if (this.work) {try{this.work.stop();}catch{}this.work=null;}
    }
    async correct(count=1, cooking=false) {
        if (!this.enabled || count<=0) return;
        this.unlock();if(!this.context)return;
        const at=this.now(), token=this.effectToken;
        // One cue per scoring response; dense checkpoints cannot build a queue.
        if (at-this.lastCorrectAt<(cooking ? this.settings.cooking_correct_interval_ms : this.settings.other_correct_interval_ms)) return;
        this.lastCorrectAt=at;
        const buffer=await this.load('correct');
        if (!buffer || !this.enabled || token!==this.effectToken || this.now()-at>this.settings.correct_max_load_age_ms) return;
        while(this.rewardSources.size>=Math.max(1, this.settings.max_reward_sources)) {
            const oldest=this.rewardSources.values().next().value;
            try{oldest.stop();}catch{}this.rewardSources.delete(oldest);
        }
        const source=this.context.createBufferSource();source.buffer=buffer;source.connect(this.rewardGain);
        this.rewardSources.add(source);source.onended=()=>{this.rewardSources.delete(source);source.disconnect();};source.start();
    }
    syncWork(state) {
        // Reward-only responses never own the task channel's lifecycle.
        if (!state) return;
        if (state.paused || state.day_ended) {this.stopAll();return;}
        const carePage = ['water_minigame','fertilizer_minigame'].includes(state.page);
        // Local press/release is authoritative for sprinkling. A queued hover
        // snapshot can still say dragging=false after a newer local press.
        const active = this.held && (carePage || (state.page==='cooking' && state.cooking?.dragging));
        if (!active) {this.stopWork();return;}
        const desired=state.page==='water_minigame'?'water':state.page==='fertilizer_minigame'?'soil':state.cooking.gesture_kind==='stir'?'cook':'cut';
        if(this.workName!==desired)this.startWork(desired);
    }
    handle(state,events=[]) {
        this.syncWork(state);
        if (state?.paused || state?.day_ended) return;
        // Layer 2 only: never stop, restart, pulse, or change gain of layer 1.
        for (const event of events) {
            if(event.kind==='correct' && event.count>0) this.correct(event.count, event.activity === 'cooking' || state?.page === 'cooking' || ['cut','cook'].includes(this.workName));
        }
    }
    stopAll() {
        this.effectToken++; this.clickToken++;
        for (const source of this.clickSources) {try {source.stop();} catch {}}
        this.clickSources.clear();
        this.inputUp();
        for(const source of this.rewardSources){try{source.stop();}catch{}}
        this.rewardSources.clear();
    }
}
if(typeof window!=='undefined')window.GameAudio=GameAudio;
if(typeof module!=='undefined')module.exports={GameAudio};
