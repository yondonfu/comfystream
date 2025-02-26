// ComfyStream Node - A custom JavaScript node for ComfyUI
// This node displays the ComfyStream UI in an iframe

const app = window.comfyAPI?.app?.app;

// Register our extension
app.registerExtension({
    name: "ComfyStream.Node",
    
    registerCustomNodes() {
        // Define our custom node class
        class ComfyStreamIframeNode extends LGraphNode {
            constructor() {
                super();
                
                // Set node properties
                this.title = "ComfyStream UI";
                this.color = "#4B9CD3"; // Blue color for the node

                
                // Create iframe element
                this.iframe = document.createElement("iframe");
                this.iframe.style.width = "100%";
                this.iframe.style.height = "100%";
                this.iframe.style.border = "none";
                this.iframe.style.borderRadius = "8px";
                
                // Set iframe source using the extension_info API
                fetch('/comfystream/extension_info')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            this.iframe.src = data.ui_url;
                        } else {
                            console.error("[ComfyStream] Error getting extension info:", data.error);
                            // Fallback to hardcoded path
                            const extensionName = "ComfyStream";
                            this.iframe.src = `/extensions/${extensionName}/static/index.html`;
                        }
                    })
                    .catch(error => {
                        console.error("[ComfyStream] Error fetching extension info:", error);
                        // Fallback to hardcoded path
                        const extensionName = "comfystream_inside";
                        this.iframe.src = `/extensions/${extensionName}/static/index.html`;
                    });
                
                // Add the iframe as a DOM widget
                this.iframeWidget = this.addDOMWidget("iframe", "UI", this.iframe, {
                    serialize: false,
                    width: this.size[0],
                    height: this.size[1] - 40
                });
                
                // Add a button to launch the UI in a new tab
                this.addWidget("button", "Open in New Tab", null, () => {
                    // Use the same endpoint as the launcher node
                    fetch('/launch_comfystream', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({})
                    })
                    .then(response => response.json())
                    .catch(error => {
                        console.error("[ComfyStream] Error launching UI:", error);
                    });
                });
                
                // Set size - make it larger to accommodate the iframe
                this.size = [700, 800];
                
                // Make the node resizable
                this.flags.resizable = true;
                
                // Handle resize to update iframe size
                const onResize = this.onResize;
                this.onResize = (size) => {
                    if (onResize) {
                        onResize.call(this, size);
                    }
                    
                    // Update iframe size when node is resized
                    if (this.iframeWidget) {
                        this.iframeWidget.width = size[0];
                        this.iframeWidget.height = size[1] - 40;
                    }
                };
            }
            
            // Handle when node is executed
            onExecute() {
                // Trigger the output
                this.triggerSlot(0);
            }
        }
        
        // Register the node type
        LiteGraph.registerNodeType("ComfyStreamUIPreview", ComfyStreamIframeNode);
        
        // Set the category
        ComfyStreamIframeNode.category = "ComfyStream";
    }
}); 