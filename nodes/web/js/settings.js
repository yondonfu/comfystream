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
        this.settings = DEFAULT_SETTINGS;
        this.loadSettings();
    }

    async loadSettings() {
        try {
            const response = await fetch('/comfystream/settings');
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            this.settings = await response.json();
            return this.settings;
        } catch (error) {
            console.error("[ComfyStream Settings] Error loading settings from server:", error);
            
            // Try to load from localStorage as fallback
            try {
                const savedSettings = localStorage.getItem('comfystream_settings');
                if (savedSettings) {
                    this.settings = { ...DEFAULT_SETTINGS, ...JSON.parse(savedSettings) };
                    
                    // Try to save these to the server
                    this.saveSettings().catch(e => {
                        console.error("[ComfyStream Settings] Failed to save localStorage settings to server:", e);
                    });
                }
            } catch (localError) {
                console.error("[ComfyStream Settings] Error loading settings from localStorage:", localError);
            }
            
            return this.settings;
        }
    }

    async saveSettings() {
        try {
            const response = await fetch('/comfystream/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.settings)
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Save to localStorage as fallback
            try {
                localStorage.setItem('comfystream_settings', JSON.stringify(this.settings));
            } catch (localError) {
                console.error("[ComfyStream Settings] Error saving to localStorage:", localError);
            }
            
            return true;
        } catch (error) {
            console.error("[ComfyStream Settings] Error saving settings to server:", error);
            
            // Try to save to localStorage as fallback
            try {
                localStorage.setItem('comfystream_settings', JSON.stringify(this.settings));
            } catch (localError) {
                console.error("[ComfyStream Settings] Error saving to localStorage:", localError);
            }
            
            return false;
        }
    }

    getSettings() {
        return this.settings;
    }

    async updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
        await this.saveSettings();
        return this.settings;
    }

    async addConfiguration(name, host, port) {
        try {
            const response = await fetch('/comfystream/settings/configuration', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'add',
                    name,
                    host,
                    port
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            if (result.success) {
                this.settings = result.settings;
                return { name, host, port };
            } else {
                throw new Error("Failed to add configuration");
            }
        } catch (error) {
            console.error("[ComfyStream Settings] Error adding configuration:", error);
            
            // Fallback to local operation
            const config = { name, host, port };
            this.settings.configurations.push(config);
            await this.saveSettings();
            return config;
        }
    }

    async removeConfiguration(index) {
        try {
            const response = await fetch('/comfystream/settings/configuration', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'remove',
                    index
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            if (result.success) {
                this.settings = result.settings;
                return true;
            } else {
                throw new Error("Failed to remove configuration");
            }
        } catch (error) {
            console.error("[ComfyStream Settings] Error removing configuration:", error);
            
            // Fallback to local operation
            if (index >= 0 && index < this.settings.configurations.length) {
                this.settings.configurations.splice(index, 1);
                
                // Update selectedConfigIndex if needed
                if (this.settings.selectedConfigIndex === index) {
                    this.settings.selectedConfigIndex = -1;
                } else if (this.settings.selectedConfigIndex > index) {
                    this.settings.selectedConfigIndex--;
                }
                
                await this.saveSettings();
                return true;
            }
            return false;
        }
    }

    async selectConfiguration(index) {
        try {
            const response = await fetch('/comfystream/settings/configuration', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'select',
                    index
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            if (result.success) {
                this.settings = result.settings;
                return true;
            } else {
                throw new Error("Failed to select configuration");
            }
        } catch (error) {
            console.error("[ComfyStream Settings] Error selecting configuration:", error);
            
            // Fallback to local operation
            if (index >= -1 && index < this.settings.configurations.length) {
                this.settings.selectedConfigIndex = index;
                
                // If a valid configuration is selected, update host and port
                if (index >= 0) {
                    const config = this.settings.configurations[index];
                    this.settings.host = config.host;
                    this.settings.port = config.port;
                }
                
                await this.saveSettings();
                return true;
            }
            return false;
        }
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

// Create a single instance of the settings manager
const settingsManager = new ComfyStreamSettings();

// Show settings modal
async function showSettingsModal() {
    // Ensure settings are loaded from server before showing modal
    await settingsManager.loadSettings();
    
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-modal");
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add CSS styles for the modal
    const styleId = "comfystream-settings-styles";
    if (!document.getElementById(styleId)) {
        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = `
            #comfystream-settings-modal {
                position: fixed;
                z-index: 10000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                backdrop-filter: blur(2px);
                animation: cs-fade-in 0.2s ease-out;
            }
            
            @keyframes cs-fade-in {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes cs-slide-in {
                from { transform: translateY(-20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            
            .cs-modal-content {
                background-color: var(--comfy-menu-bg, #202020);
                color: var(--comfy-text, #ffffff);
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 5px 25px rgba(0, 0, 0, 0.5);
                min-width: 450px;
                max-width: 80%;
                max-height: 80%;
                overflow: auto;
                position: relative;
                animation: cs-slide-in 0.2s ease-out;
                border: 1px solid var(--border-color, #444);
            }
            
            .cs-close-button {
                position: absolute;
                right: 10px;
                top: 10px;
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
                color: var(--comfy-text, #ffffff);
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background-color 0.2s;
            }
            
            .cs-close-button:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            .cs-title {
                margin-top: 0;
                margin-bottom: 20px;
                border-bottom: 1px solid var(--border-color, #444);
                padding-bottom: 10px;
                font-size: 18px;
                font-weight: 500;
            }
            
            .cs-current-config {
                margin-bottom: 15px;
                padding: 10px;
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
                border: 1px solid var(--border-color, #444);
                display: flex;
                align-items: center;
            }
            
            .cs-current-config-label {
                font-weight: bold;
                margin-right: 5px;
            }
            
            .cs-input-group {
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }
            
            .cs-label {
                width: 80px;
                font-weight: 500;
            }
            
            .cs-input {
                flex: 1;
                padding: 8px 10px;
                background-color: var(--comfy-input-bg, #111);
                color: var(--comfy-text, #fff);
                border: 1px solid var(--border-color, #444);
                border-radius: 4px;
                transition: border-color 0.2s, box-shadow 0.2s;
            }
            
            .cs-input:focus {
                outline: none;
                border-color: var(--comfy-primary-color, #4b5563);
                box-shadow: 0 0 0 2px rgba(75, 85, 99, 0.3);
            }
            
            .cs-section {
                margin-top: 20px;
            }
            
            .cs-section-title {
                margin-bottom: 10px;
                font-size: 16px;
                font-weight: 500;
            }
            
            .cs-configs-list {
                max-height: 200px;
                overflow-y: auto;
                border: 1px solid var(--border-color, #444);
                border-radius: 6px;
                padding: 5px;
                margin-bottom: 10px;
                background-color: rgba(0, 0, 0, 0.1);
            }
            
            .cs-config-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                border-bottom: 1px solid var(--border-color, #444);
                transition: background-color 0.2s;
            }
            
            .cs-config-item:last-child {
                border-bottom: none;
            }
            
            .cs-config-item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            
            .cs-config-item.selected {
                background-color: rgba(65, 105, 225, 0.2);
                border-radius: 4px;
            }
            
            .cs-config-info {
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 250px;
            }
            
            .cs-buttons-group {
                display: flex;
                gap: 5px;
            }
            
            .cs-button {
                padding: 6px 12px;
                background-color: var(--comfy-menu-bg, #202020);
                color: var(--comfy-text, #fff);
                border: 1px solid var(--border-color, #444);
                border-radius: 4px;
                cursor: pointer;
                transition: background-color 0.2s, border-color 0.2s;
                font-size: 13px;
            }
            
            .cs-button:hover:not(:disabled) {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: var(--comfy-primary-color, #4b5563);
            }
            
            .cs-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .cs-button.primary {
                background-color: var(--comfy-primary-color, #4b5563);
                border-color: var(--comfy-primary-color, #4b5563);
            }
            
            .cs-button.primary:hover {
                background-color: var(--comfy-primary-color-hover, #374151);
            }
            
            .cs-button.selected {
                background-color: rgba(65, 105, 225, 0.5);
            }
            
            .cs-button.delete:hover {
                background-color: rgba(220, 38, 38, 0.2);
                border-color: rgba(220, 38, 38, 0.5);
            }
            
            .cs-add-group {
                display: flex;
                gap: 10px;
            }
            
            .cs-footer {
                display: flex;
                justify-content: flex-end;
                margin-top: 20px;
                gap: 10px;
            }
            
            /* Scrollbar styling */
            .cs-configs-list::-webkit-scrollbar {
                width: 8px;
            }
            
            .cs-configs-list::-webkit-scrollbar-track {
                background: rgba(0, 0, 0, 0.1);
                border-radius: 4px;
            }
            
            .cs-configs-list::-webkit-scrollbar-thumb {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
            }
            
            .cs-configs-list::-webkit-scrollbar-thumb:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
            
            /* Error state */
            .cs-input.error {
                border-color: #dc2626;
                animation: cs-shake 0.4s ease-in-out;
            }
            
            @keyframes cs-shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-5px); }
                75% { transform: translateX(5px); }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Create modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-modal";
    
    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.className = "cs-modal-content";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.className = "cs-close-button";
    closeButton.onclick = () => {
        modal.remove();
    };
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "ComfyStream Server Settings";
    title.className = "cs-title";
    
    // Create settings form
    const form = document.createElement("div");
    
    // Current configuration indicator
    const currentConfigDiv = document.createElement("div");
    currentConfigDiv.className = "cs-current-config";
    
    const currentConfigLabel = document.createElement("span");
    currentConfigLabel.textContent = "Active Configuration: ";
    currentConfigLabel.className = "cs-current-config-label";
    
    const currentConfigName = document.createElement("span");
    const selectedName = settingsManager.getSelectedConfigName();
    currentConfigName.textContent = selectedName || "Custom (unsaved)";
    currentConfigName.style.fontStyle = selectedName ? "normal" : "italic";
    
    currentConfigDiv.appendChild(currentConfigLabel);
    currentConfigDiv.appendChild(currentConfigName);
    
    // Host setting
    const hostGroup = document.createElement("div");
    hostGroup.className = "cs-input-group";
    
    const hostLabel = document.createElement("label");
    hostLabel.textContent = "Host:";
    hostLabel.className = "cs-label";
    
    const hostInput = document.createElement("input");
    hostInput.id = "comfystream-host";
    hostInput.type = "text";
    hostInput.value = settingsManager.settings.host;
    hostInput.className = "cs-input";
    
    hostGroup.appendChild(hostLabel);
    hostGroup.appendChild(hostInput);
    
    // Port setting
    const portGroup = document.createElement("div");
    portGroup.className = "cs-input-group";
    
    const portLabel = document.createElement("label");
    portLabel.textContent = "Port:";
    portLabel.className = "cs-label";
    
    const portInput = document.createElement("input");
    portInput.id = "comfystream-port";
    portInput.type = "number";
    portInput.min = "1024";
    portInput.max = "65535";
    portInput.value = settingsManager.settings.port;
    portInput.className = "cs-input";
    
    portGroup.appendChild(portLabel);
    portGroup.appendChild(portInput);
    
    // Configurations section
    const configsSection = document.createElement("div");
    configsSection.className = "cs-section";
    
    const configsTitle = document.createElement("h4");
    configsTitle.textContent = "Saved Configurations";
    configsTitle.className = "cs-section-title";
    
    const configsList = document.createElement("div");
    configsList.id = "comfystream-configs-list";
    configsList.className = "cs-configs-list";
    
    const configsAddGroup = document.createElement("div");
    configsAddGroup.className = "cs-add-group";
    
    const configNameInput = document.createElement("input");
    configNameInput.id = "comfystream-config-name";
    configNameInput.type = "text";
    configNameInput.placeholder = "Configuration name";
    configNameInput.className = "cs-input";
    
    const addConfigButton = document.createElement("button");
    addConfigButton.id = "comfystream-add-config";
    addConfigButton.textContent = "Save Current";
    addConfigButton.className = "cs-button primary";
    
    configsAddGroup.appendChild(configNameInput);
    configsAddGroup.appendChild(addConfigButton);
    
    configsSection.appendChild(configsTitle);
    configsSection.appendChild(configsList);
    configsSection.appendChild(configsAddGroup);
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.className = "cs-footer";
    
    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "cs-button";
    cancelButton.onclick = () => {
        modal.remove();
    };
    
    const saveButton = document.createElement("button");
    saveButton.textContent = "Save";
    saveButton.className = "cs-button primary";
    saveButton.onclick = async () => {
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
            await settingsManager.selectConfiguration(matchingConfigIndex);
        } else {
            // No matching configuration, just update the settings
            await settingsManager.updateSettings({ 
                host, 
                port,
                selectedConfigIndex: -1 // Reset selected config since we're using custom values
            });
        }
        
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
    async function updateConfigsList() {
        configsList.innerHTML = "";
        
        if (settingsManager.settings.configurations.length === 0) {
            const emptyMessage = document.createElement("div");
            emptyMessage.textContent = "No saved configurations";
            emptyMessage.style.padding = "10px";
            emptyMessage.style.color = "var(--comfy-text-muted, #aaa)";
            emptyMessage.style.fontStyle = "italic";
            emptyMessage.style.textAlign = "center";
            configsList.appendChild(emptyMessage);
            return;
        }
        
        settingsManager.settings.configurations.forEach((config, index) => {
            const configItem = document.createElement("div");
            configItem.className = `cs-config-item ${index === settingsManager.settings.selectedConfigIndex ? 'selected' : ''}`;
            
            const configInfo = document.createElement("span");
            configInfo.className = "cs-config-info";
            configInfo.textContent = `${config.name} (${config.host}:${config.port})`;
            
            const buttonsGroup = document.createElement("div");
            buttonsGroup.className = "cs-buttons-group";
            
            const selectButton = document.createElement("button");
            selectButton.textContent = index === settingsManager.settings.selectedConfigIndex ? "Selected" : "Select";
            selectButton.className = `cs-button comfystream-config-select ${index === settingsManager.settings.selectedConfigIndex ? 'selected' : ''}`;
            selectButton.dataset.index = index;
            selectButton.disabled = index === settingsManager.settings.selectedConfigIndex;
            
            const loadButton = document.createElement("button");
            loadButton.textContent = "Load";
            loadButton.className = "cs-button comfystream-config-load";
            loadButton.dataset.index = index;
            
            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Delete";
            deleteButton.className = "cs-button delete comfystream-config-delete";
            deleteButton.dataset.index = index;
            
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
                button.addEventListener("click", async (e) => {
                    const index = parseInt(e.target.dataset.index);
                    
                    // Select the configuration and update UI
                    await settingsManager.selectConfiguration(index);
                    
                    // Update the current config display
                    const selectedName = settingsManager.getSelectedConfigName();
                    currentConfigName.textContent = selectedName || "Custom (unsaved)";
                    currentConfigName.style.fontStyle = selectedName ? "normal" : "italic";
                    
                    // Update the input fields
                    const config = settingsManager.settings.configurations[index];
                    hostInput.value = config.host;
                    portInput.value = config.port;
                    
                    // Refresh the list to update highlighting
                    await updateConfigsList();
                });
            }
        });
        
        document.querySelectorAll(".comfystream-config-load").forEach(button => {
            button.addEventListener("click", (e) => {
                const index = parseInt(e.target.dataset.index);
                const config = settingsManager.settings.configurations[index];
                hostInput.value = config.host;
                portInput.value = config.port;
            });
        });
        
        document.querySelectorAll(".comfystream-config-delete").forEach(button => {
            button.addEventListener("click", async (e) => {
                const index = parseInt(e.target.dataset.index);
                await settingsManager.removeConfiguration(index);
                
                // Update the current config display if needed
                const selectedName = settingsManager.getSelectedConfigName();
                currentConfigName.textContent = selectedName || "Custom (unsaved)";
                currentConfigName.style.fontStyle = selectedName ? "normal" : "italic";
                
                await updateConfigsList();
            });
        });
    }
    
    // Add event listener for the add config button
    addConfigButton.addEventListener("click", async () => {
        const name = configNameInput.value.trim();
        const host = hostInput.value;
        const port = parseInt(portInput.value);
        
        if (name) {
            // Add the configuration
            await settingsManager.addConfiguration(name, host, port);
            
            // Select the newly added configuration
            const newIndex = settingsManager.settings.configurations.length - 1;
            await settingsManager.selectConfiguration(newIndex);
            
            // Update the current config display
            currentConfigName.textContent = name;
            currentConfigName.style.fontStyle = "normal";
            
            // Update the list
            await updateConfigsList();
            configNameInput.value = "";
        } else {
            console.warn("[ComfyStream Settings] Cannot add config without a name");
            // Show a brief error message
            configNameInput.classList.add("error");
            setTimeout(() => {
                configNameInput.classList.remove("error");
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
    await updateConfigsList();
    
    // Focus the host input
    hostInput.focus();
}

// Export for use in other modules
export { settingsManager, showSettingsModal };

// Also keep the global for backward compatibility
window.comfyStreamSettings = {
    settingsManager,
    showSettingsModal
}; 