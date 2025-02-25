// Wait for ComfyUI to be ready
const app = window.comfyAPI?.app?.app;

// Load settings.js
(function loadSettings() {
    const script = document.createElement('script');
    script.src = './settings.js';  // Simple relative path
    script.onload = () => {
        // Settings loaded successfully
    };
    script.onerror = (e) => console.error("[ComfyStream] Error loading settings:", e);
    document.head.appendChild(script);
})();

async function controlServer(action) {
    try {
        // Get settings from the settings manager if available
        const settings = window.comfyStreamSettings?.settingsManager?.getCurrentHostPort();
        
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
        return data;
    } catch (error) {
        console.error('[ComfyStream] Error controlling server:', error);
        app.ui.dialog.show('Error', error.message || 'Failed to control ComfyStream server');
        throw error;
    }
}

async function openUI() {
    try {
        // Get settings from the settings manager if available
        const settings = window.comfyStreamSettings?.settingsManager?.getCurrentHostPort();
        
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
    if (window.comfyStreamSettings?.showSettingsModal) {
        try {
            await window.comfyStreamSettings.showSettingsModal();
        } catch (error) {
            console.error("[ComfyStream] Error showing settings modal:", error);
            app.ui.dialog.show('Error', `Failed to show settings: ${error.message}`);
        }
    } else {
        console.error("[ComfyStream] Settings module not loaded or showSettingsModal not available");
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
        const useNewMenu = app.ui.settings.store.get("Comfy.UseNewMenu");

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
    }
};

app.registerExtension(extension); 