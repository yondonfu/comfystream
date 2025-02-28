// ComfyStream Node - A custom JavaScript node for ComfyUI
// This node displays the ComfyStream UI in an iframe

const app = window.comfyAPI?.app?.app;

// Register our extension
app.registerExtension({
    name: "ComfyStream.Node",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ComfyStreamUIPreview") {
            // Set default size for the node type
            nodeType.size = [700, 800];
            
            // Save the original onNodeCreated method
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            // Override the onNodeCreated method
            nodeType.prototype.onNodeCreated = function() {
                // Set node properties before calling original method
                this.title = "ComfyStream UI";
                this.color = "#4B9CD3"; // Blue color for the node
                
                // Set size - make it larger to accommodate the iframe
                this.size = nodeType.size.slice();
                
                // Make the node resizable
                this.flags.resizable = true;
                
                // Call the original onNodeCreated method if it exists
                const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // Create iframe element
                this.iframe = document.createElement("iframe");
                this.iframe.style.width = "100%";
                this.iframe.style.height = "100%";
                this.iframe.style.border = "none";
                this.iframe.style.borderRadius = "8px";
                
                // Function to load or refresh the iframe
                this.loadIframe = () => {
                    fetch('/comfystream/extension_info')
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                // Use the current origin with the static route from extension_info
                                this.iframe.src = `${window.location.origin}${data.static_route}/index.html`;
                            } else {
                                console.error("[ComfyStream] Error getting extension info:", data.error);
                                // Fallback to hardcoded path
                                const extensionName = "comfystream";
                                this.iframe.src = `${window.location.origin}/extensions/${extensionName}/static/index.html`;
                            }
                        })
                        .catch(error => {
                            console.error("[ComfyStream] Error fetching extension info:", error);
                            // Fallback to hardcoded path
                            const extensionName = "comfystream";
                            this.iframe.src = `${window.location.origin}/extensions/${extensionName}/static/index.html`;
                        });
                };
                
                // Initial load of the iframe
                this.loadIframe();
                
                // Add the iframe as a DOM widget
                this.iframeWidget = this.addDOMWidget("iframe", "UI", this.iframe, {
                    serialize: false,
                    width: this.size[0],
                    height: this.size[1] - 40
                });
                
                // Add a button to refresh the iframe
                this.addWidget("button", "Refresh UI", null, () => {
                    console.log("[ComfyStream] Refreshing UI...");
                    if (this.iframe) {
                        // If iframe already has a src, we can just reload it
                        if (this.iframe.src) {
                            this.iframe.src = this.iframe.src;
                        } else {
                            // Otherwise load it using our function
                            this.loadIframe();
                        }
                    }
                });
                
                // Add a button to launch the UI in a new tab
                this.addWidget("button", "Open in New Tab", null, () => {
                    // Get extension info which contains the correct UI URL
                    fetch('/comfystream/extension_info', {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Use the current origin with the static route
                            const uiUrl = `${window.location.origin}${data.static_route}/index.html`;
                            // Open the URL in a new tab
                            window.open(uiUrl, '_blank');
                        }
                    })
                    .catch(error => {
                        console.error("[ComfyStream] Error launching UI:", error);
                    });
                });
                
                // Force update the iframe size after a short delay to ensure proper rendering
                setTimeout(() => {
                    this.updateIframeSize();
                }, 100);
                
                return result;
            };
            
            // Save the original onResize method
            const onResize = nodeType.prototype.onResize;
            
            // Override the onResize method
            nodeType.prototype.onResize = function(size) {
                // Call the original onResize method if it exists
                if (onResize) {
                    onResize.call(this, size);
                }
                
                this.updateIframeSize();
            };
            
            // Add a helper method to update iframe size
            nodeType.prototype.updateIframeSize = function() {
                if (this.iframeWidget) {
                    this.iframeWidget.width = this.size[0];
                    this.iframeWidget.height = this.size[1] - 40;
                    
                    // Also update the iframe element directly
                    if (this.iframe) {
                        this.iframe.style.width = this.size[0] + "px";
                        this.iframe.style.height = (this.size[1] - 40) + "px";
                    }
                    
                    // Force a canvas update
                    this.setDirtyCanvas(true, true);
                }
            };
            
            // Override the onExecute method
            nodeType.prototype.onExecute = function() {
                // Trigger the output
                this.triggerSlot(0);
            };
            
            // Override the default size method
            nodeType.prototype.getSize = function() {
                return [this.size[0], this.size[1]];
            };
            
            // Override the computeSize method to maintain our size
            nodeType.prototype.computeSize = function() {
                return [this.size[0], this.size[1]];
            };
            
            // Override the onAdded method to ensure size is set when added to graph
            const onAdded = nodeType.prototype.onAdded;
            nodeType.prototype.onAdded = function() {
                if (onAdded) {
                    onAdded.call(this);
                }
                
                // Ensure size is set correctly when added to graph
                this.size = nodeType.size.slice();
                
                // Force a size update
                setTimeout(() => {
                    this.updateIframeSize();
                    this.setDirtyCanvas(true, true);
                }, 100);
            };
        }
    }
}); 