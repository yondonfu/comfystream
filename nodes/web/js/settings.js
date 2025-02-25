// ComfyStream Settings Manager
console.log("[ComfyStream Settings] Initializing settings module");

const DEFAULT_SETTINGS = {
    host: "0.0.0.0",
    port: 8889,
    configurations: [],
    selectedConfigIndex: -1  // -1 means no configuration is selected
};

class ComfyStreamSettings {
    constructor() {
        console.log("[ComfyStream Settings] Creating settings instance");
        this.settings = this.loadSettings();
        console.log("[ComfyStream Settings] Settings loaded:", this.settings);
    }

    loadSettings() {
        try {
            console.log("[ComfyStream Settings] Loading settings from localStorage");
            const savedSettings = localStorage.getItem('comfystream_settings');
            if (savedSettings) {
                console.log("[ComfyStream Settings] Found saved settings");
                return { ...DEFAULT_SETTINGS, ...JSON.parse(savedSettings) };
            }
        } catch (error) {
            console.error("[ComfyStream Settings] Error loading settings:", error);
        }
        console.log("[ComfyStream Settings] Using default settings");
        return { ...DEFAULT_SETTINGS };
    }

    saveSettings() {
        try {
            console.log("[ComfyStream Settings] Saving settings to localStorage");
            localStorage.setItem('comfystream_settings', JSON.stringify(this.settings));
        } catch (error) {
            console.error("[ComfyStream Settings] Error saving settings:", error);
        }
    }

    getSettings() {
        return this.settings;
    }

    updateSettings(newSettings) {
        console.log("[ComfyStream Settings] Updating settings:", newSettings);
        this.settings = { ...this.settings, ...newSettings };
        this.saveSettings();
        return this.settings;
    }

    addConfiguration(name, host, port) {
        console.log("[ComfyStream Settings] Adding configuration:", name, host, port);
        const config = { name, host, port };
        this.settings.configurations.push(config);
        this.saveSettings();
        return config;
    }

    removeConfiguration(index) {
        console.log("[ComfyStream Settings] Removing configuration at index:", index);
        if (index >= 0 && index < this.settings.configurations.length) {
            this.settings.configurations.splice(index, 1);
            
            // Update selectedConfigIndex if needed
            if (this.settings.selectedConfigIndex === index) {
                // The selected config was deleted
                this.settings.selectedConfigIndex = -1;
            } else if (this.settings.selectedConfigIndex > index) {
                // The selected config is after the deleted one, adjust index
                this.settings.selectedConfigIndex--;
            }
            
            this.saveSettings();
            return true;
        }
        return false;
    }

    selectConfiguration(index) {
        console.log("[ComfyStream Settings] Selecting configuration at index:", index);
        if (index >= -1 && index < this.settings.configurations.length) {
            this.settings.selectedConfigIndex = index;
            
            // If a valid configuration is selected, update host and port
            if (index >= 0) {
                const config = this.settings.configurations[index];
                this.settings.host = config.host;
                this.settings.port = config.port;
            }
            
            this.saveSettings();
            return true;
        }
        return false;
    }

    getCurrentHostPort() {
        return {
            host: this.settings.host,
            port: this.settings.port
        };
    }
    
    getSelectedConfigName() {
        if (this.settings.selectedConfigIndex >= 0 && 
            this.settings.selectedConfigIndex < this.settings.configurations.length) {
            return this.settings.configurations[this.settings.selectedConfigIndex].name;
        }
        return null;
    }
}

// Create settings instance
console.log("[ComfyStream Settings] Creating settings manager instance");
const settingsManager = new ComfyStreamSettings();

// Show settings modal
function showSettingsModal() {
    console.log("[ComfyStream Settings] showSettingsModal called");
    
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-modal");
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-modal";
    modal.style.position = "fixed";
    modal.style.zIndex = "10000";
    modal.style.left = "0";
    modal.style.top = "0";
    modal.style.width = "100%";
    modal.style.height = "100%";
    modal.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
    modal.style.display = "flex";
    modal.style.justifyContent = "center";
    modal.style.alignItems = "center";
    
    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.style.backgroundColor = "var(--comfy-menu-bg, #202020)";
    modalContent.style.color = "var(--comfy-text, #ffffff)";
    modalContent.style.borderRadius = "8px";
    modalContent.style.padding = "20px";
    modalContent.style.boxShadow = "0 0 20px rgba(0, 0, 0, 0.5)";
    modalContent.style.minWidth = "450px";
    modalContent.style.maxWidth = "80%";
    modalContent.style.maxHeight = "80%";
    modalContent.style.overflow = "auto";
    modalContent.style.position = "relative";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.style.position = "absolute";
    closeButton.style.right = "10px";
    closeButton.style.top = "10px";
    closeButton.style.background = "none";
    closeButton.style.border = "none";
    closeButton.style.fontSize = "20px";
    closeButton.style.cursor = "pointer";
    closeButton.style.color = "var(--comfy-text, #ffffff)";
    closeButton.onclick = () => {
        modal.remove();
    };
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "ComfyStream Server Settings";
    title.style.marginTop = "0";
    title.style.marginBottom = "20px";
    title.style.borderBottom = "1px solid var(--border-color, #444)";
    title.style.paddingBottom = "10px";
    
    // Create settings form
    const form = document.createElement("div");
    
    // Current configuration indicator
    const currentConfigDiv = document.createElement("div");
    currentConfigDiv.style.marginBottom = "15px";
    currentConfigDiv.style.padding = "8px";
    currentConfigDiv.style.backgroundColor = "rgba(0, 0, 0, 0.2)";
    currentConfigDiv.style.borderRadius = "4px";
    currentConfigDiv.style.border = "1px solid var(--border-color, #444)";
    
    const currentConfigLabel = document.createElement("span");
    currentConfigLabel.textContent = "Active Configuration: ";
    currentConfigLabel.style.fontWeight = "bold";
    
    const currentConfigName = document.createElement("span");
    const selectedName = settingsManager.getSelectedConfigName();
    currentConfigName.textContent = selectedName || "Custom (unsaved)";
    currentConfigName.style.fontStyle = selectedName ? "normal" : "italic";
    
    currentConfigDiv.appendChild(currentConfigLabel);
    currentConfigDiv.appendChild(currentConfigName);
    
    // Host setting
    const hostGroup = document.createElement("div");
    hostGroup.style.marginBottom = "15px";
    hostGroup.style.display = "flex";
    hostGroup.style.alignItems = "center";
    
    const hostLabel = document.createElement("label");
    hostLabel.textContent = "Host:";
    hostLabel.style.width = "80px";
    
    const hostInput = document.createElement("input");
    hostInput.id = "comfystream-host";
    hostInput.type = "text";
    hostInput.value = settingsManager.settings.host;
    hostInput.style.flex = "1";
    hostInput.style.padding = "5px";
    hostInput.style.backgroundColor = "var(--comfy-input-bg, #111)";
    hostInput.style.color = "var(--comfy-text, #fff)";
    hostInput.style.border = "1px solid var(--border-color, #444)";
    hostInput.style.borderRadius = "4px";
    
    hostGroup.appendChild(hostLabel);
    hostGroup.appendChild(hostInput);
    
    // Port setting
    const portGroup = document.createElement("div");
    portGroup.style.marginBottom = "15px";
    portGroup.style.display = "flex";
    portGroup.style.alignItems = "center";
    
    const portLabel = document.createElement("label");
    portLabel.textContent = "Port:";
    portLabel.style.width = "80px";
    
    const portInput = document.createElement("input");
    portInput.id = "comfystream-port";
    portInput.type = "number";
    portInput.min = "1024";
    portInput.max = "65535";
    portInput.value = settingsManager.settings.port;
    portInput.style.flex = "1";
    portInput.style.padding = "5px";
    portInput.style.backgroundColor = "var(--comfy-input-bg, #111)";
    portInput.style.color = "var(--comfy-text, #fff)";
    portInput.style.border = "1px solid var(--border-color, #444)";
    portInput.style.borderRadius = "4px";
    
    portGroup.appendChild(portLabel);
    portGroup.appendChild(portInput);
    
    // Configurations section
    const configsSection = document.createElement("div");
    configsSection.style.marginTop = "20px";
    
    const configsTitle = document.createElement("h4");
    configsTitle.textContent = "Saved Configurations";
    configsTitle.style.marginBottom = "10px";
    
    const configsList = document.createElement("div");
    configsList.id = "comfystream-configs-list";
    configsList.style.maxHeight = "200px";
    configsList.style.overflowY = "auto";
    configsList.style.border = "1px solid var(--border-color, #444)";
    configsList.style.borderRadius = "4px";
    configsList.style.padding = "5px";
    configsList.style.marginBottom = "10px";
    
    const configsAddGroup = document.createElement("div");
    configsAddGroup.style.display = "flex";
    configsAddGroup.style.gap = "10px";
    
    const configNameInput = document.createElement("input");
    configNameInput.id = "comfystream-config-name";
    configNameInput.type = "text";
    configNameInput.placeholder = "Configuration name";
    configNameInput.style.flex = "1";
    configNameInput.style.padding = "5px";
    configNameInput.style.backgroundColor = "var(--comfy-input-bg, #111)";
    configNameInput.style.color = "var(--comfy-text, #fff)";
    configNameInput.style.border = "1px solid var(--border-color, #444)";
    configNameInput.style.borderRadius = "4px";
    
    const addConfigButton = document.createElement("button");
    addConfigButton.id = "comfystream-add-config";
    addConfigButton.textContent = "Save Current";
    addConfigButton.style.padding = "5px 10px";
    addConfigButton.style.backgroundColor = "var(--comfy-menu-bg, #202020)";
    addConfigButton.style.color = "var(--comfy-text, #fff)";
    addConfigButton.style.border = "1px solid var(--border-color, #444)";
    addConfigButton.style.borderRadius = "4px";
    addConfigButton.style.cursor = "pointer";
    
    configsAddGroup.appendChild(configNameInput);
    configsAddGroup.appendChild(addConfigButton);
    
    configsSection.appendChild(configsTitle);
    configsSection.appendChild(configsList);
    configsSection.appendChild(configsAddGroup);
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.style.display = "flex";
    footer.style.justifyContent = "flex-end";
    footer.style.marginTop = "20px";
    footer.style.gap = "10px";
    
    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.style.padding = "8px 16px";
    cancelButton.style.backgroundColor = "var(--comfy-menu-bg, #202020)";
    cancelButton.style.color = "var(--comfy-text, #fff)";
    cancelButton.style.border = "1px solid var(--border-color, #444)";
    cancelButton.style.borderRadius = "4px";
    cancelButton.style.cursor = "pointer";
    cancelButton.onclick = () => {
        modal.remove();
    };
    
    const saveButton = document.createElement("button");
    saveButton.textContent = "Save";
    saveButton.style.padding = "8px 16px";
    saveButton.style.backgroundColor = "var(--comfy-menu-bg, #202020)";
    saveButton.style.color = "var(--comfy-text, #fff)";
    saveButton.style.border = "1px solid var(--border-color, #444)";
    saveButton.style.borderRadius = "4px";
    saveButton.style.cursor = "pointer";
    saveButton.onclick = () => {
        const host = hostInput.value;
        const port = parseInt(portInput.value);
        
        // If the current values match a saved configuration, select it
        let matchingConfigIndex = -1;
        settingsManager.settings.configurations.forEach((config, index) => {
            if (config.host === host && config.port === port) {
                matchingConfigIndex = index;
            }
        });
        
        if (matchingConfigIndex >= 0) {
            settingsManager.selectConfiguration(matchingConfigIndex);
        } else {
            // No matching configuration, just update the settings
            settingsManager.updateSettings({ 
                host, 
                port,
                selectedConfigIndex: -1 // Reset selected config since we're using custom values
            });
        }
        
        console.log("[ComfyStream Settings] Settings saved");
        modal.remove();
    };
    
    footer.appendChild(cancelButton);
    footer.appendChild(saveButton);
    
    // Assemble the modal
    form.appendChild(currentConfigDiv);
    form.appendChild(hostGroup);
    form.appendChild(portGroup);
    form.appendChild(configsSection);
    
    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
    
    // Update configurations list
    function updateConfigsList() {
        console.log("[ComfyStream Settings] Updating configurations list");
        configsList.innerHTML = "";
        
        if (settingsManager.settings.configurations.length === 0) {
            const emptyMessage = document.createElement("div");
            emptyMessage.textContent = "No saved configurations";
            emptyMessage.style.padding = "10px";
            emptyMessage.style.color = "var(--comfy-text-muted, #aaa)";
            emptyMessage.style.fontStyle = "italic";
            configsList.appendChild(emptyMessage);
            return;
        }
        
        settingsManager.settings.configurations.forEach((config, index) => {
            const configItem = document.createElement("div");
            configItem.style.display = "flex";
            configItem.style.justifyContent = "space-between";
            configItem.style.alignItems = "center";
            configItem.style.padding = "8px 5px";
            configItem.style.borderBottom = index < settingsManager.settings.configurations.length - 1 ? 
                "1px solid var(--border-color, #444)" : "none";
                
            // Highlight the selected configuration
            if (index === settingsManager.settings.selectedConfigIndex) {
                configItem.style.backgroundColor = "rgba(65, 105, 225, 0.2)";
                configItem.style.borderRadius = "4px";
            }
            
            const configInfo = document.createElement("span");
            configInfo.textContent = `${config.name} (${config.host}:${config.port})`;
            
            const buttonsGroup = document.createElement("div");
            buttonsGroup.style.display = "flex";
            buttonsGroup.style.gap = "5px";
            
            const selectButton = document.createElement("button");
            selectButton.textContent = index === settingsManager.settings.selectedConfigIndex ? "Selected" : "Select";
            selectButton.className = "comfystream-config-select";
            selectButton.dataset.index = index;
            selectButton.style.padding = "3px 8px";
            selectButton.style.backgroundColor = index === settingsManager.settings.selectedConfigIndex ? 
                "rgba(65, 105, 225, 0.5)" : "var(--comfy-menu-bg, #202020)";
            selectButton.style.color = "var(--comfy-text, #fff)";
            selectButton.style.border = "1px solid var(--border-color, #444)";
            selectButton.style.borderRadius = "4px";
            selectButton.style.cursor = "pointer";
            selectButton.style.fontSize = "12px";
            selectButton.disabled = index === settingsManager.settings.selectedConfigIndex;
            
            const loadButton = document.createElement("button");
            loadButton.textContent = "Load";
            loadButton.className = "comfystream-config-load";
            loadButton.dataset.index = index;
            loadButton.style.padding = "3px 8px";
            loadButton.style.backgroundColor = "var(--comfy-menu-bg, #202020)";
            loadButton.style.color = "var(--comfy-text, #fff)";
            loadButton.style.border = "1px solid var(--border-color, #444)";
            loadButton.style.borderRadius = "4px";
            loadButton.style.cursor = "pointer";
            loadButton.style.fontSize = "12px";
            
            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Delete";
            deleteButton.className = "comfystream-config-delete";
            deleteButton.dataset.index = index;
            deleteButton.style.padding = "3px 8px";
            deleteButton.style.backgroundColor = "var(--comfy-menu-bg, #202020)";
            deleteButton.style.color = "var(--comfy-text, #fff)";
            deleteButton.style.border = "1px solid var(--border-color, #444)";
            deleteButton.style.borderRadius = "4px";
            deleteButton.style.cursor = "pointer";
            deleteButton.style.fontSize = "12px";
            
            buttonsGroup.appendChild(selectButton);
            buttonsGroup.appendChild(loadButton);
            buttonsGroup.appendChild(deleteButton);
            
            configItem.appendChild(configInfo);
            configItem.appendChild(buttonsGroup);
            
            configsList.appendChild(configItem);
        });
        
        // Add event listeners
        document.querySelectorAll(".comfystream-config-select").forEach(button => {
            if (!button.disabled) {
                button.addEventListener("click", (e) => {
                    const index = parseInt(e.target.dataset.index);
                    console.log("[ComfyStream Settings] Selecting config at index:", index);
                    
                    // Select the configuration and update UI
                    settingsManager.selectConfiguration(index);
                    
                    // Update the current config display
                    const selectedName = settingsManager.getSelectedConfigName();
                    currentConfigName.textContent = selectedName || "Custom (unsaved)";
                    currentConfigName.style.fontStyle = selectedName ? "normal" : "italic";
                    
                    // Update the input fields
                    const config = settingsManager.settings.configurations[index];
                    hostInput.value = config.host;
                    portInput.value = config.port;
                    
                    // Refresh the list to update highlighting
                    updateConfigsList();
                });
            }
        });
        
        document.querySelectorAll(".comfystream-config-load").forEach(button => {
            button.addEventListener("click", (e) => {
                const index = parseInt(e.target.dataset.index);
                console.log("[ComfyStream Settings] Loading config at index:", index);
                const config = settingsManager.settings.configurations[index];
                hostInput.value = config.host;
                portInput.value = config.port;
            });
        });
        
        document.querySelectorAll(".comfystream-config-delete").forEach(button => {
            button.addEventListener("click", (e) => {
                const index = parseInt(e.target.dataset.index);
                console.log("[ComfyStream Settings] Deleting config at index:", index);
                settingsManager.removeConfiguration(index);
                
                // Update the current config display if needed
                const selectedName = settingsManager.getSelectedConfigName();
                currentConfigName.textContent = selectedName || "Custom (unsaved)";
                currentConfigName.style.fontStyle = selectedName ? "normal" : "italic";
                
                updateConfigsList();
            });
        });
    }
    
    // Add event listener for the add config button
    addConfigButton.addEventListener("click", () => {
        console.log("[ComfyStream Settings] Add config button clicked");
        const name = configNameInput.value.trim();
        const host = hostInput.value;
        const port = parseInt(portInput.value);
        
        if (name) {
            // Add the configuration
            settingsManager.addConfiguration(name, host, port);
            
            // Select the newly added configuration
            const newIndex = settingsManager.settings.configurations.length - 1;
            settingsManager.selectConfiguration(newIndex);
            
            // Update the current config display
            currentConfigName.textContent = name;
            currentConfigName.style.fontStyle = "normal";
            
            // Update the list
            updateConfigsList();
            configNameInput.value = "";
        } else {
            console.warn("[ComfyStream Settings] Cannot add config without a name");
            // Show a brief error message
            configNameInput.style.borderColor = "red";
            setTimeout(() => {
                configNameInput.style.borderColor = "var(--border-color, #444)";
            }, 2000);
        }
    });
    
    // Add event listeners for input changes
    hostInput.addEventListener("input", () => {
        // When user changes the input, check if it still matches the selected config
        const selectedIndex = settingsManager.settings.selectedConfigIndex;
        if (selectedIndex >= 0) {
            const config = settingsManager.settings.configurations[selectedIndex];
            if (hostInput.value !== config.host || parseInt(portInput.value) !== config.port) {
                // Values no longer match the selected config
                currentConfigName.textContent = "Custom (unsaved)";
                currentConfigName.style.fontStyle = "italic";
            } else {
                // Values match the selected config again
                currentConfigName.textContent = config.name;
                currentConfigName.style.fontStyle = "normal";
            }
        }
    });
    
    portInput.addEventListener("input", () => {
        // Same check for port changes
        const selectedIndex = settingsManager.settings.selectedConfigIndex;
        if (selectedIndex >= 0) {
            const config = settingsManager.settings.configurations[selectedIndex];
            if (hostInput.value !== config.host || parseInt(portInput.value) !== config.port) {
                currentConfigName.textContent = "Custom (unsaved)";
                currentConfigName.style.fontStyle = "italic";
            } else {
                currentConfigName.textContent = config.name;
                currentConfigName.style.fontStyle = "normal";
            }
        }
    });
    
    // Initial update of configurations list
    updateConfigsList();
    
    // Focus the host input
    hostInput.focus();
    
    console.log("[ComfyStream Settings] Dialog setup complete");
}

// Export for use in other modules
console.log("[ComfyStream Settings] Exporting settings to window object");
window.comfyStreamSettings = {
    settingsManager,
    showSettingsModal
}; 