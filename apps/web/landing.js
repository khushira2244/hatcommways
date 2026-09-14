/* Informational workflow selector; no application state or API calls. */
(() => {
  const steps = [...document.querySelectorAll('.landing-step')];
  const cards = [...document.querySelectorAll('.landing-workflow-card')];
  steps.forEach(step => {
    step.addEventListener('click', () => {
      steps.forEach(button => {
        const selected = button === step;
        button.classList.toggle('is-highlighted', selected);
        button.setAttribute('aria-pressed', String(selected));
      });
      cards.forEach(card => {
        card.hidden = card.id !== step.getAttribute('aria-controls');
      });
    });
  });
})();
