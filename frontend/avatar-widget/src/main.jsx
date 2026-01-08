import { render } from 'preact';
import { App } from './app';
import './index.css';

const WIDGET_ID = 'bizdnaii-avatar-widget-container';

function init() {
  let container = document.getElementById(WIDGET_ID);
  if (!container) {
    container = document.createElement('div');
    container.id = WIDGET_ID;
    document.body.appendChild(container);
  }
  render(<App />, container);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
