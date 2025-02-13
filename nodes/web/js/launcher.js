const app = window.comfyAPI?.app?.app;
console.log("[ComfyStream] Launcher extension loading, app:", app);

if (!app) {
    console.error("[ComfyStream] Failed to get app instance!");
}

// Register our custom widget
app.registerExtension({
    name: "ComfyStream.LauncherButton",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        // Only handle our launcher node
        if (nodeData.name !== "ComfyStreamLauncher") return;
        
        console.log("[ComfyStream] Processing ComfyStreamLauncher node");

        // Add launch method to handle server communication
        nodeType.prototype.launchComfyStream = async function() {
            console.log("[ComfyStream] launchComfyStream called");
            try {
                const response = await fetch('/launch_comfystream', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ 
                        node_id: this.id 
                    })
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
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
            }
        };

        // Override the onNodeCreated method
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        console.log("[ComfyStream] Original onNodeCreated:", onNodeCreated);
        
        nodeType.prototype.onNodeCreated = function() {
            console.log("[ComfyStream] onNodeCreated called");
            // Call the original onNodeCreated if it exists
            if (onNodeCreated) {
                console.log("[ComfyStream] Calling original onNodeCreated");
                onNodeCreated.apply(this);
            }

            // Add the button widget directly
            console.log("[ComfyStream] Adding button widget");
            const widget = this.addWidget("button", "Launch ComfyStream", null, () => {
                this.launchComfyStream();
            });
            widget.serialize = false;
            console.log("[ComfyStream] Button widget added:", widget);
        };
        console.log("[ComfyStream] Node setup complete");
    }
}); 