// Mount the passive display and give visible loading/error feedback.
const status = document.getElementById('visual-load-status');
const button = document.getElementById('show-visual');
function reveal() {
    const panel = document.querySelector('.dotdew-observer');
    if (!panel) return;
    panel.scrollIntoView({block:'start', behavior:'smooth'});
    panel.setAttribute('tabindex','-1');
    panel.focus({preventScroll:true});
}
try {
    const viewer = await import('./viewer.js?v=2');
    await viewer.ready;
    status.textContent = 'Visual display ready';
    button.onclick = reveal;
    const panel = document.querySelector('.dotdew-observer');
    const back = document.createElement('button');
    back.type = 'button'; back.textContent = 'Game pad';
    back.onclick = () => document.getElementById('dotpad').scrollIntoView({block:'center',behavior:'smooth'});
    panel.querySelector('.dv-tools').prepend(back);
    if (new URL(location.href).searchParams.get('view') === 'visual') {
        requestAnimationFrame(() => requestAnimationFrame(reveal));
    }
} catch (error) {
    status.classList.add('visual-error');
    status.textContent = 'Visual display failed to load. Copy the complete web/spectator folder and reload.';
    console.warn('Visual display unavailable', error);
}
