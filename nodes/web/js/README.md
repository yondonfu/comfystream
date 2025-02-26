# ComfyStream Status Indicator

This module provides a flexible status indicator for the ComfyStream server using Web Components. It can be used in multiple files and displayed in multiple locations on the screen.

## Basic Usage

```javascript
// Import the status indicator module
import { startStatusPolling } from './status-indicator.js';

// Start polling and create a default indicator
startStatusPolling();
```

## Customizing the Indicator

You can customize the appearance of the indicator using CSS variables:

```javascript
import { startStatusPolling } from './status-indicator.js';

// Create a customized indicator
const indicator = startStatusPolling({
    size: '16px',          // Size of the indicator
    color-running: 'blue', // Color when server is running
    color-stopped: 'red'   // Color when server is stopped
});

// Position it using CSS
indicator.style.position = 'fixed';
indicator.style.bottom = '20px';
indicator.style.right = '20px';
indicator.style.zIndex = '9000';
```

## Multiple Indicators

You can create multiple indicators in different locations:

```javascript
import { createStatusIndicator, startStatusPolling } from './status-indicator.js';

// Start polling with default indicator
startStatusPolling();

// Create additional indicators
const topRightIndicator = createStatusIndicator();
topRightIndicator.style.position = 'fixed';
topRightIndicator.style.top = '10px';
topRightIndicator.style.right = '10px';

const bottomLeftIndicator = createStatusIndicator();
bottomLeftIndicator.style.position = 'fixed';
bottomLeftIndicator.style.bottom = '10px';
bottomLeftIndicator.style.left = '10px';
```

## Custom Containers

You can place indicators inside custom containers:

```javascript
import { createStatusIndicator } from './status-indicator.js';

// Create a container element
const container = document.createElement('div');
container.style.position = 'fixed';
container.style.top = '50px';
container.style.left = '50px';
container.style.padding = '10px';
document.body.appendChild(container);

// Create an indicator inside this container
const containerIndicator = createStatusIndicator();
container.appendChild(containerIndicator);
```

## Listening for Status Changes

You can listen for status changes on any indicator:

```javascript
import { createStatusIndicator } from './status-indicator.js';

const indicator = createStatusIndicator();
indicator.addEventListener('status-changed', (event) => {
    console.log('Server status changed:', event.detail);
    // event.detail contains { running, host, port }
});
```

## Removing Indicators

You can remove indicators when they're no longer needed:

```javascript
import { removeStatusIndicator, stopStatusPolling } from './status-indicator.js';

// Remove a specific indicator
removeStatusIndicator(myIndicator);

// Or stop all polling and remove all indicators
stopStatusPolling();
```

## CSS Variables

The indicator supports the following CSS variables:

```css
--indicator-size: 12px;                                /* Size of the indicator */
--indicator-color-running: #4CAF50;                    /* Color when running */
--indicator-color-stopped: #F44336;                    /* Color when stopped */
--indicator-border-color: #666;                        /* Border color */
--indicator-shadow-color-running: rgba(76, 175, 80, 0.6); /* Shadow when running */
--indicator-shadow-color-stopped: rgba(244, 67, 54, 0.6); /* Shadow when stopped */
```

## API Reference

### Functions

- `startStatusPolling(options, container)`: Starts the status polling and creates a default indicator
- `createStatusIndicator(options)`: Creates a new status indicator
- `updateStatusIndicator(status)`: Updates all indicators with new status
- `pollServerStatus(immediate)`: Polls the server for status
- `removeStatusIndicator(indicator)`: Removes a specific indicator
- `stopStatusPolling()`: Stops polling and removes all indicators

### Web Component

The module defines a custom element `<comfystream-status-indicator>` that can be used directly in HTML:

```html
<comfystream-status-indicator style="--indicator-size: 16px;"></comfystream-status-indicator>
``` 