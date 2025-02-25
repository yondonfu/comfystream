// Wait for ComfyUI to be ready
const app = window.comfyAPI?.app?.app;
console.log("[ComfyStream] Initializing with app:", app);

// Load settings.js
(function loadSettings() {
    console.log("[ComfyStream] Attempting to load settings.js");
    const script = document.createElement('script');
    script.src = './settings.js';  // Simple relative path
    script.onload = () => {
        console.log("[ComfyStream] Settings loaded successfully");
        console.log("[ComfyStream] Settings object:", window.comfyStreamSettings);
    };
    script.onerror = (e) => console.error("[ComfyStream] Error loading settings:", e);
    document.head.appendChild(script);
})();

async function controlServer(action) {
    console.log("[ComfyStream] Controlling server with action:", action);
    try {
        // Get settings from the settings manager if available
        const settings = window.comfyStreamSettings?.settingsManager?.getCurrentHostPort();
        console.log("[ComfyStream] Using settings:", settings);
        
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
        console.log("[ComfyStream] Server control response:", data);
        return data;
    } catch (error) {
        console.error('[ComfyStream] Error controlling server:', error);
        app.ui.dialog.show('Error', error.message || 'Failed to control ComfyStream server');
        throw error;
    }
}

async function openUI() {
    console.log("[ComfyStream] Attempting to open UI");
    try {
        // Get settings from the settings manager if available
        const settings = window.comfyStreamSettings?.settingsManager?.getCurrentHostPort();
        console.log("[ComfyStream] Using settings for UI:", settings);
        
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
        console.log("[ComfyStream] Launch response:", data);
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
function openSettings() {
    console.log("[ComfyStream] Opening settings modal");
    console.log("[ComfyStream] Settings object available:", !!window.comfyStreamSettings);
    
    if (window.comfyStreamSettings?.showSettingsModal) {
        console.log("[ComfyStream] Calling showSettingsModal function");
        try {
            window.comfyStreamSettings.showSettingsModal();
            console.log("[ComfyStream] Modal should be displayed now");
        } catch (error) {
            console.error("[ComfyStream] Error showing settings modal:", error);
            app.ui.dialog.show('Error', `Failed to show settings: ${error.message}`);
        }
    } else {
        console.error("[ComfyStream] Settings module not loaded or showSettingsModal not available");
        console.log("[ComfyStream] Available properties:", Object.keys(window.comfyStreamSettings || {}));
        app.ui.dialog.show('Error', 'Settings module not loaded properly');
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
        console.log("[ComfyStream] Setting up extension");
        const useNewMenu = app.ui.settings.store.get("Comfy.UseNewMenu");
        console.log("[ComfyStream] Menu setting:", useNewMenu);

        if (useNewMenu === "Disabled") {
            // Old menu system
            console.log("[ComfyStream] Using old menu system");
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
        } else {
            // New menu system is handled automatically by the menuCommands registration
            console.log("[ComfyStream] Using new menu system");
        }
    }
};

console.log("[ComfyStream] Registering extension:", extension);
app.registerExtension(extension);
console.log("[ComfyStream] Extension registered"); 