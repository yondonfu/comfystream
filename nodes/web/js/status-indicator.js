// ComfyStream Status Indicator
// This module provides a web component for the ComfyStream server status indicator

// Define the custom element
class ComfyStreamStatusIndicator extends HTMLElement {
  constructor() {
    super();
    
    // Create a shadow DOM for encapsulation
    this.attachShadow({ mode: 'open' });
    
    // Initialize state
    this.state = {
      running: false,
      starting: false,
      stopping: false,
      host: null,
      port: null,
      polling: false,
      pollInterval: null
    };
    
    // Initial render
    this.render();
    
    // Start polling when created
    this.startPolling();
  }
  
  // Lifecycle callbacks
  connectedCallback() {
    // Listen for theme changes
    this.observeThemeChanges();
    
    // Make sure we're visible
    this.style.display = 'inline-block';
  }
  
  disconnectedCallback() {
    this.stopPolling();
    
    // Clean up any observers
    if (this.themeObserver) {
      this.themeObserver.disconnect();
    }
  }
  
  // Observe theme changes to adapt colors
  observeThemeChanges() {
    // Use MutationObserver to detect theme changes (light/dark mode)
    this.themeObserver = new MutationObserver((mutations) => {
      // Check for class changes on body or html that might indicate theme changes
      for (const mutation of mutations) {
        if (mutation.type === 'attributes' && 
            (mutation.attributeName === 'class' || mutation.attributeName === 'data-theme')) {
          this.updateThemeColors();
        }
      }
    });
    
    // Start observing
    this.themeObserver.observe(document.documentElement, { attributes: true });
    this.themeObserver.observe(document.body, { attributes: true });
    
    // Initial theme check
    this.updateThemeColors();
  }
  
  // Update colors based on current theme
  updateThemeColors() {
    // Check if we're in dark mode
    const isDarkMode = document.documentElement.classList.contains('dark') || 
                      document.body.classList.contains('dark') ||
                      window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Update CSS variables based on theme
    if (isDarkMode) {
      this.style.setProperty('--indicator-border-color', '#888');
    } else {
      this.style.setProperty('--indicator-border-color', '#444');
    }
  }
  
  // Get label text based on attributes or default
  getLabelText() {
    // Check if custom labels are provided via attributes
    const runningLabel = this.getAttribute('running-label') || '';
    const stoppedLabel = this.getAttribute('stopped-label') || '';
    const startingLabel = this.getAttribute('starting-label') || '';
    const stoppingLabel = this.getAttribute('stopping-label') || '';
    
    // Use custom labels if provided, otherwise use minimal default
    if (this.state.starting) {
      return startingLabel || (this.hasAttribute('minimal-label') ? 'Starting' : '');
    } else if (this.state.stopping) {
      return stoppingLabel || (this.hasAttribute('minimal-label') ? 'Stopping' : '');
    } else if (this.state.running) {
      return runningLabel || (this.hasAttribute('minimal-label') ? 'Running' : '');
    } else {
      return stoppedLabel || (this.hasAttribute('minimal-label') ? 'Stopped' : '');
    }
  }
  
  // Render the component
  render() {
    // Get label text
    const labelText = this.getLabelText();
    
    // Determine indicator color based on state
    let indicatorColor, indicatorShadowColor;
    
    if (this.state.starting) {
      indicatorColor = 'var(--indicator-color-starting, #FFA500)'; // Orange for starting
      indicatorShadowColor = 'var(--indicator-shadow-color-starting, rgba(255, 165, 0, 0.6))';
    } else if (this.state.stopping) {
      indicatorColor = 'var(--indicator-color-stopping, #FFC107)'; // Amber for stopping
      indicatorShadowColor = 'var(--indicator-shadow-color-stopping, rgba(255, 193, 7, 0.6))';
    } else if (this.state.running) {
      indicatorColor = 'var(--indicator-color-running)';
      indicatorShadowColor = 'var(--indicator-shadow-color-running)';
    } else {
      indicatorColor = 'var(--indicator-color-stopped)';
      indicatorShadowColor = 'var(--indicator-shadow-color-stopped)';
    }
    
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: inline-block;
          /* Default styles that can be overridden by the parent */
          --indicator-size: 10px;
          --indicator-color-running: #4CAF50;
          --indicator-color-stopped: #F44336;
          --indicator-color-starting: #FFA500;
          --indicator-color-stopping: #FFC107;
          --indicator-border-color: #666;
          --indicator-shadow-color-running: rgba(76, 175, 80, 0.9);
          --indicator-shadow-color-stopped: rgba(244, 67, 54, 0.9);
          --indicator-shadow-color-starting: rgba(255, 165, 0, 0.9);
          --indicator-shadow-color-stopping: rgba(255, 193, 7, 0.9);
        }
        
        .container {
          display: flex;
          align-items: center;
          background-color: transparent;
          padding: 4px 0;
          border-radius: 12px;
          box-shadow: none;
        }
        
        .indicator {
          width: var(--indicator-size);
          height: var(--indicator-size);
          border-radius: 50%;
          background-color: ${indicatorColor};
          border: 1px solid var(--indicator-border-color);
          box-shadow: 0 0 3px ${indicatorShadowColor};
          transition: all 0.3s ease;
          flex-shrink: 0;
        }
        
        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.3); }
          100% { transform: scale(1); }
        }
        
        @keyframes blink {
          0% { opacity: 0.4; }
          50% { opacity: 1; }
          100% { opacity: 0.4; }
        }
        
        .pulse {
          animation: pulse 0.3s ease-in-out;
        }
        
        .blink {
          animation: blink 1.5s infinite ease-in-out;
        }
        
        /* Label styling */
        .label {
          font-size: 12px;
          margin-left: 6px;
          color: white;
          font-family: Arial, sans-serif;
          white-space: nowrap;
          display: ${(this.hasAttribute('show-label') && labelText) ? 'inline' : 'none'};
        }
      </style>
      <div class="container">
        <div class="indicator ${this.state.starting || this.state.stopping ? 'blink' : ''}" title="${this.getTitle()}"></div>
        <span class="label">${labelText}</span>
      </div>
    `;
  }
  
  // Update the status
  updateStatus(status) {
    const wasRunning = this.state.running;
    const willBeRunning = status.running;
    
    // Update state
    this.state = { ...this.state, ...status };
    
    // Re-render
    this.render();
    
    // Add pulse animation if status changed
    if (wasRunning !== willBeRunning) {
      const indicator = this.shadowRoot.querySelector('.indicator');
      indicator.classList.add('pulse');
      setTimeout(() => {
        indicator.classList.remove('pulse');
      }, 300);
    }
  }
  
  // Get the title text
  getTitle() {
    if (this.state.starting) {
      return 'ComfyStream Server: Starting...';
    } else if (this.state.stopping) {
      return 'ComfyStream Server: Stopping...';
    } else if (this.state.running) {
      return `ComfyStream Server: Running on ${this.state.host || 'localhost'}:${this.state.port}`;
    } else {
      return 'ComfyStream Server: Stopped';
    }
  }
  
  // Start polling
  startPolling() {
    // Poll immediately
    this.pollStatus(true);
    
    // Set up interval polling (every 5 seconds)
    if (!this.state.pollInterval) {
      this.state.pollInterval = setInterval(() => this.pollStatus(), 5000);
    }
  }
  
  // Stop polling
  stopPolling() {
    if (this.state.pollInterval) {
      clearInterval(this.state.pollInterval);
      this.state.pollInterval = null;
    }
  }
  
  // Poll for status
  async pollStatus(immediate = false) {
    // Prevent multiple polling processes
    if (this.state.polling && !immediate) return;
    
    this.state.polling = true;
    
    try {
      const response = await fetch('/comfystream/control', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ action: 'status' })
      });
      
      if (response.ok) {
        const data = await response.json();
        const wasRunning = this.state.running;
        const willBeRunning = data.status.running;
        if (wasRunning !== willBeRunning) {
          console.log('[ComfyStream] Server status changed:', willBeRunning ? 'Running' : 'Stopped');
        }
        
        this.updateStatus(data.status);
        
        // Dispatch an event that other components can listen for
        this.dispatchEvent(new CustomEvent('status-changed', { 
          detail: data.status,
          bubbles: true,
          composed: true
        }));
      } else {
        if (this.state.running) {
          console.log('[ComfyStream] Server status error, assuming stopped');
        }
        this.updateStatus({ running: false });
      }
    } catch (error) {
      if (this.state.running) {
        console.log('[ComfyStream] Server connection error:', error.message);
      }
      this.updateStatus({ running: false });
    } finally {
      this.state.polling = false;
    }
  }
  
  // Static get observedAttributes
  static get observedAttributes() {
    return ['show-label', 'running-label', 'stopped-label', 'starting-label', 'stopping-label', 'minimal-label'];
  }
  
  // Attribute changed callback
  attributeChangedCallback(name, oldValue, newValue) {
    // Re-render when any of our observed attributes change
    this.render();
  }
}

// Register the custom element
customElements.define('comfystream-status-indicator', ComfyStreamStatusIndicator);

// Global registry for indicators
const indicatorRegistry = {
  indicators: [],
  mainIndicator: null
};

/**
 * Create a status indicator element
 * @param {Object} options - Configuration options (CSS properties)
 * @returns {HTMLElement} The created indicator element
 */
function createStatusIndicator(options = {}) {
  // Create the indicator element
  const indicator = document.createElement('comfystream-status-indicator');
  
  // Apply any custom CSS properties and attributes
  Object.entries(options).forEach(([key, value]) => {
    if (key === 'showLabel' && value) {
      indicator.setAttribute('show-label', '');
    } else if (key === 'runningLabel' && value) {
      indicator.setAttribute('running-label', value);
    } else if (key === 'stoppedLabel' && value) {
      indicator.setAttribute('stopped-label', value);
    } else if (key === 'startingLabel' && value) {
      indicator.setAttribute('starting-label', value);
    } else if (key === 'stoppingLabel' && value) {
      indicator.setAttribute('stopping-label', value);
    } else if (key === 'minimalLabel' && value) {
      indicator.setAttribute('minimal-label', '');
    } else if (key.startsWith('--')) {
      // CSS variables that start with --
      indicator.style.setProperty(key, value);
    } else {
      // Regular CSS variables
      indicator.style.setProperty(`--indicator-${key}`, value);
    }
  });
  
  // Add to registry
  indicatorRegistry.indicators.push(indicator);
  
  return indicator;
}

/**
 * Start status polling and create a default indicator
 * @param {Object} options - Options for the indicator
 * @param {HTMLElement} container - Container to append the indicator to
 * @returns {HTMLElement} The created indicator element
 */
function startStatusPolling(options = {}, container = document.body) {
  // If we already have a main indicator, return it
  if (indicatorRegistry.mainIndicator) {
    return indicatorRegistry.mainIndicator;
  }
  
  // Create the indicator
  const indicator = createStatusIndicator(options);
  
  // Add to container
  container.appendChild(indicator);
  
  // Store as main indicator
  indicatorRegistry.mainIndicator = indicator;
  
  return indicator;
}

/**
 * Update all status indicators
 * @param {Object} status - Status information
 */
function updateStatusIndicator(status) {
  // Dispatch a custom event that all indicators will listen for
  document.dispatchEvent(new CustomEvent('comfystream-status-update', { 
    detail: status 
  }));
  
  // Also update each indicator directly
  indicatorRegistry.indicators.forEach(indicator => {
    if (indicator instanceof ComfyStreamStatusIndicator) {
      indicator.updateStatus(status);
    }
  });
}

/**
 * Poll server status
 * @param {boolean} immediate - Whether to poll immediately
 */
function pollServerStatus(immediate = false) {
  // If we have a main indicator, use its polling method
  if (indicatorRegistry.mainIndicator) {
    indicatorRegistry.mainIndicator.pollStatus(immediate);
  }
}

/**
 * Remove a status indicator
 * @param {HTMLElement} indicator - The indicator to remove
 */
function removeStatusIndicator(indicator) {
  const index = indicatorRegistry.indicators.indexOf(indicator);
  if (index !== -1) {
    indicatorRegistry.indicators.splice(index, 1);
    
    // If it's the main indicator, clear that reference
    if (indicator === indicatorRegistry.mainIndicator) {
      indicatorRegistry.mainIndicator = null;
    }
    
    // Remove from DOM
    indicator.remove();
  }
}

/**
 * Stop status polling and remove all indicators
 */
function stopStatusPolling() {
  // Remove all indicators
  indicatorRegistry.indicators.forEach(indicator => {
    indicator.remove();
  });
  
  indicatorRegistry.indicators = [];
  indicatorRegistry.mainIndicator = null;
}

// Export the functions that will be used by other modules
export {
  startStatusPolling,
  createStatusIndicator,
  updateStatusIndicator,
  pollServerStatus,
  removeStatusIndicator,
  stopStatusPolling
}; 