// Wait for ComfyUI to be ready
import { startStatusPolling, updateStatusIndicator, pollServerStatus } from './status-indicator.js';
import { settingsManager, showSettingsModal } from './settings.js';

const app = window.comfyAPI?.app?.app;

// Store our indicator reference
let statusIndicator = null;

// Initialize the status indicator as soon as possible
function initializeStatusIndicator() {
    if (!statusIndicator) {
        // Create the indicator with CSS variables for styling
        statusIndicator = startStatusPolling({
            size: '10px',  // Slightly smaller to fit in menu
            showLabel: false,  // No label needed since it's next to menu text
            runningLabel: '',
            stoppedLabel: '',
            startingLabel: '',
            stoppingLabel: '',
            minimalLabel: true
        });
        
        // Add a CSS class for styling
        statusIndicator.classList.add('comfystream-status-indicator');
        
        // Try to find the ComfyStream menu item label
        const findAndInjectIndicator = () => {
            // Don't use :contains() as it's not standard CSS - use the general approach instead
            const menuItems = document.querySelectorAll('.p-menubar-item-label');
            for (const item of menuItems) {
                if (item.textContent.includes('ComfyStream')) {
                    // Insert the indicator after the menu label
                    item.parentNode.insertBefore(statusIndicator, item.nextSibling);
                    return true;
                }
            }
            
            return false;
        };
        
        // Try to inject immediately
        const injected = findAndInjectIndicator();
        
        // If not successful, set up a mutation observer to watch for menu changes
        if (!injected) {
            const observer = new MutationObserver((mutations) => {
                if (findAndInjectIndicator()) {
                    observer.disconnect();
                }
            });
            
            observer.observe(document.body, { 
                childList: true, 
                subtree: true 
            });
            
            // Also try again when the menu extension is registered
            document.addEventListener('comfy-extension-registered', (event) => {
                if (event.detail?.name === "ComfyStream.Menu") {
                    setTimeout(findAndInjectIndicator, 100);
                }
            });
        }
        
        // Force an immediate status check
        pollServerStatus(true);
        
        // Create and inject CSS for positioning
        const style = document.createElement('style');
        style.textContent = `
            .comfystream-status-indicator {
                display: inline-block;
                margin-left: 2px;
                vertical-align: middle;
                position: relative;
                top: -1px;
            }
        `;
        document.head.appendChild(style);
    }
}

// Try to initialize immediately if app is available
if (app) {
    initializeStatusIndicator();
} else {
    // If app isn't ready yet, wait for DOMContentLoaded
    window.addEventListener('DOMContentLoaded', () => {
        initializeStatusIndicator();
    });
}

// Also initialize when the extension is registered
document.addEventListener('comfy-extension-registered', (event) => {
    if (event.detail?.name === "ComfyStream.Menu") {
        initializeStatusIndicator();
    }
});

async function controlServer(action) {
    try {
        // Get settings from the settings manager
        const settings = settingsManager.getCurrentHostPort();
        
        // Set transitional state based on action
        if (action === 'start') {
            updateStatusIndicator({ starting: true, running: false, stopping: false });
        } else if (action === 'stop') {
            updateStatusIndicator({ stopping: true, running: true, starting: false });
        } else if (action === 'restart') {
            updateStatusIndicator({ stopping: true, running: true, starting: false });
        }
        
        const response = await fetch('/comfystream/control', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ 
                action,
                settings
            })
        });
        
        if (!response.ok) {
            // Reset transitional states on error
            if (action === 'start') {
                updateStatusIndicator({ starting: false });
            } else if (action === 'stop' || action === 'restart') {
                updateStatusIndicator({ stopping: false });
            }
            
            const errorText = await response.text();
            console.error("[ComfyStream] Server returned error response:", response.status, errorText);
            try {
                const errorData = JSON.parse(errorText);
                throw new Error(errorData.error || `Server error: ${response.status}`);
            } catch (e) {
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }
        }

        const data = await response.json();
        
        // Update status indicator after control action
        if (data.status) {
            // Clear transitional states
            data.status.starting = false;
            data.status.stopping = false;
            updateStatusIndicator(data.status);
        }
        
        return data;
    } catch (error) {
        // Reset any transitional states on error
        if (action === 'start') {
            updateStatusIndicator({ starting: false });
        } else if (action === 'stop' || action === 'restart') {
            updateStatusIndicator({ stopping: false });
        }
        
        console.error('[ComfyStream] Error controlling server:', error);
        app.ui.dialog.show('Error', error.message || 'Failed to control ComfyStream server');
        throw error;
    }
}

async function openUI() {
    try {
        // Get settings from the settings manager
        const settings = settingsManager.getCurrentHostPort();
        
        const response = await fetch('/launch_comfystream', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ settings })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error("[ComfyStream] UI launch returned error response:", response.status, errorText);
            try {
                const errorData = JSON.parse(errorText);
                throw new Error(errorData.error || `Server error: ${response.status}`);
            } catch (e) {
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }
        }

        const data = await response.json();
        data.url = "./extensions/comfystream/static/index.html"
        if (!data.success) {
            throw new Error(data.error || 'Unknown error launching ComfyStream');
        }
    } catch (error) {
        console.error('[ComfyStream] Error launching ComfyStream:', error);
        app.ui.dialog.show('Error', error.message || 'Failed to launch ComfyStream');
        throw error;
    }
}

// Function to open settings modal
async function openSettings() {
    try {
        await showSettingsModal();
    } catch (error) {
        console.error("[ComfyStream] Error showing settings modal:", error);
        app.ui.dialog.show('Error', `Failed to show settings: ${error.message}`);
    }
}

// Register our extension
const extension = {
    name: "ComfyStream.Menu",
    
    // Define commands that will be used by menu items
    commands: [
        {
            id: "ComfyStream.OpenUI",
            icon: "pi pi-external-link",
            label: "Open ComfyStream UI",
            function: openUI
        },
        {
            id: "ComfyStream.StartServer", 
            icon: "pi pi-play",
            label: "Start ComfyStream Server",
            function: async () => {
                await controlServer('start');
            }
        },
        {
            id: "ComfyStream.StopServer",
            icon: "pi pi-stop", 
            label: "Stop ComfyStream Server",
            function: async () => {
                await controlServer('stop');
            }
        },
        {
            id: "ComfyStream.RestartServer",
            icon: "pi pi-refresh",
            label: "Restart ComfyStream Server", 
            function: async () => {
                await controlServer('restart');
            }
        },
        {
            id: "ComfyStream.Settings",
            icon: "pi pi-cog",
            label: "Server Settings",
            function: openSettings
        }
    ],

    // Define where these commands appear in the menu
    menuCommands: [
        {
            path: ["ComfyStream"],
            commands: [
                "ComfyStream.OpenUI",
                null, // Separator
                "ComfyStream.StartServer",
                "ComfyStream.StopServer", 
                "ComfyStream.RestartServer",
                null, // Separator
                "ComfyStream.Settings"
            ]
        }
    ],

    // Setup function to handle menu registration based on settings
    setup() {
        let useNewMenu = "Enabled"; // Default to new menu system
        
        // Safely check if the settings store exists
        try {
            if (app.ui.settings && app.ui.settings.store && typeof app.ui.settings.store.get === 'function') {
                useNewMenu = app.ui.settings.store.get("Comfy.UseNewMenu") || "Enabled";
            }
        } catch (e) {
            console.log("[ComfyStream] Could not access settings store, defaulting to new menu system");
        }

        if (useNewMenu === "Disabled") {
            // Old menu system
            const menu = app.ui.menu;
            menu.addSeparator();
            const comfyStreamMenu = menu.addMenu("ComfyStream");
            comfyStreamMenu.addItem("Open UI", openUI, { icon: "pi pi-external-link" });
            comfyStreamMenu.addSeparator();
            comfyStreamMenu.addItem("Start Server", () => controlServer('start'), { icon: "pi pi-play" });
            comfyStreamMenu.addItem("Stop Server", () => controlServer('stop'), { icon: "pi pi-stop" });
            comfyStreamMenu.addItem("Restart Server", () => controlServer('restart'), { icon: "pi pi-refresh" });
            comfyStreamMenu.addSeparator();
            comfyStreamMenu.addItem("Server Settings", openSettings, { icon: "pi pi-cog" });
        }
        // New menu system is handled automatically by the menuCommands registration
        
        // Make sure the status indicator is initialized
        initializeStatusIndicator();
    }
};

app.registerExtension(extension); 