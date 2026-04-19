const audioContext = typeof AudioContext !== 'undefined' ? new AudioContext() : null;
const playTone = () => {
  if (!audioContext) return;
  const osc = audioContext.createOscillator();
  const gain = audioContext.createGain();
  osc.type = 'triangle';
  osc.frequency.setValueAtTime(440, audioContext.currentTime);
  gain.gain.setValueAtTime(0.03, audioContext.currentTime);
  osc.connect(gain);
  gain.connect(audioContext.destination);
  osc.start();
  setTimeout(() => {
    gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.1);
    osc.stop(audioContext.currentTime + 0.1);
  }, 80);
};

export function initHoverSound(selector = '[data-hover-sound]') {
  if (!audioContext) return;
  document.querySelectorAll(selector).forEach((element) => {
    element.addEventListener('mouseenter', () => {
      if (audioContext.state === 'suspended') {
        audioContext.resume().then(playTone).catch(() => {});
        return;
      }
      playTone();
    });
  });
}
