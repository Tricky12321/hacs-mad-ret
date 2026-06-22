class MadPlanPanel extends HTMLElement {
  constructor() {
    super();
    this._iframe = null;
    this._hass = null;
    this._onMsg = this._onMsg.bind(this);
  }

  connectedCallback() {
    if (this._iframe) return;
    Object.assign(this.style, { display: 'block', width: '100%', height: '100%' });
    this._iframe = document.createElement('iframe');
    Object.assign(this._iframe.style, { width: '100%', height: '100%', border: 'none', display: 'block' });
    // Cache-bust so frontend updates appear on a plain browser refresh — no HA restart needed
    this._iframe.src = '/mad-plan-static/index.html?v=' + Date.now();
    this.appendChild(this._iframe);
    this._iframe.addEventListener('load', () => this._send());
    window.addEventListener('message', this._onMsg);
  }

  disconnectedCallback() {
    window.removeEventListener('message', this._onMsg);
  }

  set hass(hass) {
    this._hass = hass;
    this._send();
  }

  _send() {
    const token = this._hass?.auth?.data?.access_token;
    if (!token || !this._iframe?.contentWindow) return;
    this._iframe.contentWindow.postMessage(
      { type: 'mad_plan_auth', access_token: token },
      window.location.origin
    );
  }

  _onMsg(e) {
    if (e.data?.type === 'mad_plan_request_auth') this._send();
  }
}

customElements.define('mad-plan-panel', MadPlanPanel);
