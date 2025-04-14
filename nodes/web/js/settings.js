// ComfyStream Settings Manager
console.log("[ComfyStream Settings] Initializing settings module");
const app = window.comfyAPI?.app?.app;

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

    async manageComfystream(action_type, action, data) {
        try {
            const response = await fetch('/comfystream/settings/manage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action_type: action_type,
                    action: action,
                    payload: data
                })
            });
            
            const result = await response.json();

            if (response.ok) {
                return result;
            } else {
                throw new Error(`${result.error}`);
            }
        } catch (error) {
            throw error;
        }
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
            .comfystream-settings-modal {
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

            .cs-help-text {
                display: none;
                width: 400px;
                padding-left: 80px;
                padding-bottom: 10px;
                padding-top: 0px;
                margin-top: 0px;
                font-size: 0.75em;
                overflow-wrap: break-word;
                font-style: italic;
            }

            .loader {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                display: inline-block;
                position: relative;
                border: 2px solid;
                border-color: #FFF #FFF transparent transparent;
                box-sizing: border-box;
                animation: rotation 1s linear infinite;
            }
            .loader::after,
            .loader::before {
                content: '';  
                box-sizing: border-box;
                position: absolute;
                left: 0;
                right: 0;
                top: 0;
                bottom: 0;
                margin: auto;
                border: 2px solid;
                border-color: transparent transparent #FF3D00 #FF3D00;
                width: 16px;
                height: 16px;
                border-radius: 50%;
                box-sizing: border-box;
                animation: rotationBack 0.5s linear infinite;
                transform-origin: center center;
            }
            .loader::before {
                width: 13px;
                height: 13px;
                border-color: #FFF #FFF transparent transparent;
                animation: rotation 1.5s linear infinite;
            }
                    
            @keyframes rotation {
                0% {
                    transform: rotate(0deg);
                }
                100% {
                    transform: rotate(360deg);
                }
            } 
            @keyframes rotationBack {
                0% {
                    transform: rotate(0deg);
                }
                100% {
                    transform: rotate(-360deg);
                }
            }
    
        `;
        document.head.appendChild(style);
    }
    
    // Create modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-modal";
    modal.className = "comfystream-settings-modal";
    
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
    
    // Comfystream mgmt api actions
    // Nodes management group
    const nodesGroup = document.createElement("div");
    nodesGroup.className = "cs-input-group";

    const nodesLabel = document.createElement("label");
    nodesLabel.textContent = "Nodes:";
    nodesLabel.className = "cs-label";

    const installNodeButton = document.createElement("button");
    installNodeButton.textContent = "Install";
    installNodeButton.className = "cs-button";

    const updateNodeButton = document.createElement("button");
    updateNodeButton.textContent = "Update";
    updateNodeButton.className = "cs-button";

    const deleteNodeButton = document.createElement("button");
    deleteNodeButton.textContent = "Delete";
    deleteNodeButton.className = "cs-button";

    const toggleNodeButton = document.createElement("button");
    toggleNodeButton.textContent = "Enable/Disable";
    toggleNodeButton.className = "cs-button";

    const loadingNodes = document.createElement("span");
    loadingNodes.id = "comfystream-loading-nodes-spinner";
    loadingNodes.className = "loader";
    loadingNodes.style.display = "none"; // Initially hidden

    nodesGroup.appendChild(nodesLabel);
    nodesGroup.appendChild(installNodeButton);
    nodesGroup.appendChild(updateNodeButton);
    nodesGroup.appendChild(deleteNodeButton);
    nodesGroup.appendChild(toggleNodeButton);
    nodesGroup.appendChild(loadingNodes);

    // Models management group
    const modelsGroup = document.createElement("div");
    modelsGroup.className = "cs-input-group";

    const modelsLabel = document.createElement("label");
    modelsLabel.textContent = "Models:";
    modelsLabel.className = "cs-label";

    const addModelButton = document.createElement("button");
    addModelButton.textContent = "Add";
    addModelButton.className = "cs-button";

    const deleteModelButton = document.createElement("button");
    deleteModelButton.textContent = "Delete";
    deleteModelButton.className = "cs-button";
    
    const loadingModels = document.createElement("span");
    loadingModels.id = "comfystream-loading-models-spinner";
    loadingModels.className = "loader";
    loadingModels.style.display = "none"; // Initially hidden

    modelsGroup.appendChild(modelsLabel);
    modelsGroup.appendChild(addModelButton);
    modelsGroup.appendChild(deleteModelButton);
    modelsGroup.appendChild(loadingModels);

    // turn server creds group
    const turnServerCredsGroup = document.createElement("div");
    turnServerCredsGroup.className = "cs-input-group";

    const turnServerCredsLabel = document.createElement("label");
    turnServerCredsLabel.textContent = "TURN Creds:";
    turnServerCredsLabel.className = "cs-label";

    const setButton = document.createElement("button");
    setButton.textContent = "Set";
    setButton.className = "cs-button";
    
    const turnServerCredsLoading = document.createElement("span");
    turnServerCredsLoading.id = "comfystream-loading-turn-server-creds-spinner";
    turnServerCredsLoading.className = "loader";
    turnServerCredsLoading.style.display = "none"; // Initially hidden

    turnServerCredsGroup.appendChild(turnServerCredsLabel);
    turnServerCredsGroup.appendChild(setButton);
    turnServerCredsGroup.appendChild(turnServerCredsLoading);

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
    
    const msgTxt = document.createElement("div");
    msgTxt.id = "comfystream-msg-txt";
    msgTxt.className = "cs-msg-text";

    footer.appendChild(cancelButton);
    footer.appendChild(saveButton);
    
    // Assemble the modal
    form.appendChild(currentConfigDiv);
    form.appendChild(hostGroup);
    form.appendChild(portGroup);
    form.appendChild(nodesGroup);
    form.appendChild(modelsGroup);
    form.appendChild(turnServerCredsGroup);
    form.appendChild(configsSection);
    
    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    modalContent.appendChild(msgTxt);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
    
    async function manageNodes(action) {
        //show the spinner to provide feedback
        const loadingSpinner = document.getElementById("comfystream-loading-nodes-spinner");
        loadingSpinner.style.display = "inline-block";

        try {
            if (action === "install") {
                await showInstallNodesModal();
            } else if (action === "update") {
                await showUpdateNodesModal();
            } else if (action === "delete") {
                await showDeleteNodesModal();
            } else if (action === "toggle") {
                await showToggleNodesModal();
            }
            
            // Hide the spinner after action
            loadingSpinner.style.display = "none"; 
        } catch (error) {
            console.error("[ComfyStream] Error installing node:", error);
            app.ui.dialog.show('Error', `Failed to install node: ${error.message}`);
        }
    }
    async function manageModels(action) {
        //show the spinner to provide feedback
        const loadingSpinner = document.getElementById("comfystream-loading-models-spinner");
        loadingSpinner.style.display = "inline-block";

        try {
            if (action === "add") {
                await showAddModelsModal();
            } else if (action === "delete") {
                await showDeleteModelsModal();
            }
            // Hide the spinner after action
            loadingSpinner.style.display = "none"; 
        } catch (error) {
            console.error("[ComfyStream] Error managing models:", error);
            app.ui.dialog.show('Error', `Failed to manage models: ${error.message}`);
        }
    }
    async function manageTurnServerCredentials(action) {
        //show the spinner to provide feedback
        const loadingSpinner = document.getElementById("comfystream-loading-turn-server-creds-spinner");
        loadingSpinner.style.display = "inline-block";

        try {
            if (action === "set") {
                await showSetTurnServerCredsModal();
            } else if (action === "clear") {
                await showClearTurnServerCredsModal();
            }
            // Hide the spinner after action
            loadingSpinner.style.display = "none"; 
        } catch (error) {
            console.error("[ComfyStream] Error managing TURN server credentials:", error);
            app.ui.dialog.show('Error', `Failed to manage TURN server credentials: ${error.message}`);
        }

        // Hide the spinner after action
        loadingSpinner.style.display = "none"; 
    }
    // Add event listeners for nodes management buttons
    installNodeButton.addEventListener("click", () => {
        manageNodes("install");
    });
    updateNodeButton.addEventListener("click", () => {
        manageNodes("update");
    });
    deleteNodeButton.addEventListener("click", () => {
        manageNodes("delete");
    });
    toggleNodeButton.addEventListener("click", () => {
        manageNodes("toggle");
    });
    // Add event listeners for models management buttons
    addModelButton.addEventListener("click", () => {
        manageModels("add");
    });
    deleteModelButton.addEventListener("click", () => {
        manageModels("delete");
    });
    setButton.addEventListener("click", async () => {
        await showSetTurnServerCredsModal();
    });
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

async function showSetTurnServerCredsModal() {
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-set-turn-creds-modal");
    if (existingModal) {
        existingModal.remove();
    }    

    // Create nodes mgmt modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-set-turn-creds-modal";
    modal.className = "comfystream-settings-modal";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.className = "cs-close-button";
    closeButton.onclick = () => {
        modal.remove();
    };

    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.className = "cs-modal-content";
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "Set TURN Server Credentials";
    title.className = "cs-title";
    
    // Create settings form
    const form = document.createElement("div");

    // account type
    const accountTypeGroup = document.createElement("div");
    accountTypeGroup.className = "cs-input-group";
    
    const accountTypeLabel = document.createElement("label");
    accountTypeLabel.textContent = "Account Type:";
    accountTypeLabel.className = "cs-label";
    
    const accountTypeSelect = document.createElement("select");
    const accountItem = document.createElement("option");
    accountItem.value = "twilio";
    accountItem.textContent = "Twilio";
    accountTypeSelect.appendChild(accountItem);
    accountTypeSelect.id = "comfystream-selected-turn-server-account-type";
    
    const accountTypeHelpIcon = document.createElement("span");
    accountTypeHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    accountTypeHelpIcon.style.cursor = "pointer";
    accountTypeHelpIcon.style.marginLeft = "5px";
    accountTypeHelpIcon.title = "Click for help";
    
    const accountTypeHelp = document.createElement("div");
    accountTypeHelp.textContent = "Specify the account type to use";
    accountTypeHelp.className = "cs-help-text";
    accountTypeHelp.style.display = "none";

    accountTypeHelpIcon.addEventListener("click", () => {
        if (accountTypeHelp.style.display == "none") {
            accountTypeHelp.style.display = "block";
        } else {
            accountTypeHelp.style.display = "none";
        }
    });

    accountTypeGroup.appendChild(accountTypeLabel);
    accountTypeGroup.appendChild(accountTypeSelect);
    accountTypeGroup.appendChild(accountTypeHelpIcon);

    // account id
    const accountIdGroup = document.createElement("div");
    accountIdGroup.className = "cs-input-group";
    
    const accountIdLabel = document.createElement("label");
    accountIdLabel.textContent = "Account ID:";
    accountIdLabel.className = "cs-label";
        
    const accountIdInput = document.createElement("input");
    accountIdInput.id = "turn-server-creds-account-id";
    accountIdInput.className = "cs-input";
    
    
    const accountIdHelpIcon = document.createElement("span");
    accountIdHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    accountIdHelpIcon.style.cursor = "pointer";
    accountIdHelpIcon.style.marginLeft = "5px";
    accountIdHelpIcon.title = "Click for help";
    
    const accountIdHelp = document.createElement("div");
    accountIdHelp.textContent = "Specify the account id for Twilio TURN server credentials";
    accountIdHelp.className = "cs-help-text";
    accountIdHelp.style.display = "none";

    accountIdHelpIcon.addEventListener("click", () => {
        if (accountIdHelp.style.display == "none") {
            accountIdHelp.style.display = "block";
        } else {
            accountIdHelp.style.display = "none";
        }
    });

    accountIdGroup.appendChild(accountIdLabel);
    accountIdGroup.appendChild(accountIdInput);
    accountIdGroup.appendChild(accountIdHelpIcon);
    
    // auth token
    const accountAuthTokenGroup = document.createElement("div");
    accountAuthTokenGroup.className = "cs-input-group";
    
    const accountAuthTokenLabel = document.createElement("label");
    accountAuthTokenLabel.textContent = "Auth Token:";
    accountAuthTokenLabel.className = "cs-label";
    
    const accountAuthTokenInput = document.createElement("input");
    accountAuthTokenInput.id = "turn-server-creds-auth-token";
    accountAuthTokenInput.className = "cs-input";
    
    const accountAuthTokenHelpIcon = document.createElement("span");
    accountAuthTokenHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    accountAuthTokenHelpIcon.style.cursor = "pointer";
    accountAuthTokenHelpIcon.style.marginLeft = "5px";
    accountAuthTokenHelpIcon.title = "Click for help";
    accountAuthTokenHelpIcon.style.position = "relative";

    const accountAuthTokenHelp = document.createElement("div");
    accountAuthTokenHelp.textContent = "Specify the auth token provided by Twilio for TURN server credentials";
    accountAuthTokenHelp.className = "cs-help-text";
    accountAuthTokenHelp.style.display = "none";
    
    accountAuthTokenHelpIcon.addEventListener("click", () => {
        if (accountAuthTokenHelp.style.display == "none") {
            accountAuthTokenHelp.style.display = "block";
        } else {
            accountAuthTokenHelp.style.display = "none";
        }
    });

    accountAuthTokenGroup.appendChild(accountAuthTokenLabel);
    accountAuthTokenGroup.appendChild(accountAuthTokenInput);
    accountAuthTokenGroup.appendChild(accountAuthTokenHelpIcon);    
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.className = "cs-footer";
    
    const msgTxt = document.createElement("div");
    msgTxt.id = "comfystream-manage-turn-server-creds-msg-txt";
    msgTxt.style.fontSize = "0.75em";
    msgTxt.style.fontStyle = "italic";
    msgTxt.style.overflowWrap = "break-word";

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "cs-button";
    cancelButton.onclick = () => {
        modal.remove();
    };
    const clearButton = document.createElement("button");
    clearButton.textContent = "Clear";
    clearButton.className = "cs-button";
    clearButton.onclick = () => {
        const accountType = accountTypeSelect.options[accountTypeSelect.selectedIndex].value;
        msgTxt.textContent = setTurnSeverCreds(accountType, "", "");
    };

    const setButton = document.createElement("button");
    setButton.textContent = "Set";
    setButton.className = "cs-button primary";
    setButton.onclick = async () => {
        const accountId = accountIdInput.value;
        const authToken = accountAuthTokenInput.value;
        const accountType = accountTypeSelect.options[accountTypeSelect.selectedIndex].value;
        msgTxt.textContent = setTurnSeverCreds(accountType, accountId, authToken);        
    };

    footer.appendChild(msgTxt);
    footer.appendChild(cancelButton);
    footer.appendChild(setButton);
    
    // Assemble the modal
    form.appendChild(accountTypeGroup);
    form.appendChild(accountTypeHelp);
    form.appendChild(accountIdGroup);
    form.appendChild(accountIdHelp);
    form.appendChild(accountAuthTokenGroup);
    form.appendChild(accountAuthTokenHelp);

    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
}

async function setTurnSeverCreds(accountType, accountId, authToken) {
    try {
        const payload = {
            type: accountType,
            account_id: accountId,
            auth_token: authToken
        }

        await settingsManager.manageComfystream( 
            "turn/server", 
            "set/account",
            [payload]
        );
        return "TURN server credentials updated successfully";
    } catch (error) {
        console.error("[ComfyStream] Error adding model:", error);
        msgTxt.textContent = error;
    }
}

async function showAddModelsModal() {
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-add-model-modal");
    if (existingModal) {
        existingModal.remove();
    }    

    // Create nodes mgmt modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-add-model-modal";
    modal.className = "comfystream-settings-modal";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.className = "cs-close-button";
    closeButton.onclick = () => {
        modal.remove();
    };

    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.className = "cs-modal-content";
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "Add Model";
    title.className = "cs-title";
    
    // Create settings form
    const form = document.createElement("div");

    // URL of node to add
    const modelUrlGroup = document.createElement("div");
    modelUrlGroup.className = "cs-input-group";
    
    const modelUrlLabel = document.createElement("label");
    modelUrlLabel.textContent = "Url:";
    modelUrlLabel.className = "cs-label";
    
    const modelUrlInput = document.createElement("input");
    modelUrlInput.id = "add-model-url";
    modelUrlInput.className = "cs-input";
    
    
    const modelUrlHelpIcon = document.createElement("span");
    modelUrlHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    modelUrlHelpIcon.style.cursor = "pointer";
    modelUrlHelpIcon.style.marginLeft = "5px";
    modelUrlHelpIcon.title = "Click for help";
    
    const modelUrlHelp = document.createElement("div");
    modelUrlHelp.textContent = "Specify the url of the model download url";
    modelUrlHelp.className = "cs-help-text";
    modelUrlHelp.style.display = "none";

    modelUrlHelpIcon.addEventListener("click", () => {
        if (modelUrlHelp.style.display == "none") {
            modelUrlHelp.style.display = "block";
        } else {
            modelUrlHelp.style.display = "none";
        }
    });

    modelUrlGroup.appendChild(modelUrlLabel);
    modelUrlGroup.appendChild(modelUrlInput);
    modelUrlGroup.appendChild(modelUrlHelpIcon);
    
    // branch of node to add
    const modelTypeGroup = document.createElement("div");
    modelTypeGroup.className = "cs-input-group";
    
    const modelTypeLabel = document.createElement("label");
    modelTypeLabel.textContent = "Type:";
    modelTypeLabel.className = "cs-label";
    
    const modelTypeInput = document.createElement("input");
    modelTypeInput.id = "add-node-branch";
    modelTypeInput.className = "cs-input";
    
    const modelTypeHelpIcon = document.createElement("span");
    modelTypeHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    modelTypeHelpIcon.style.cursor = "pointer";
    modelTypeHelpIcon.style.marginLeft = "5px";
    modelTypeHelpIcon.title = "Click for help";
    modelTypeHelpIcon.style.position = "relative";

    const modelTypeHelp = document.createElement("div");
    modelTypeHelp.textContent = "Specify the type of model that is the top level folder under 'models' folder (e.g. 'checkpoints' = models/checkpoints)";
    modelTypeHelp.className = "cs-help-text";
    modelTypeHelp.style.display = "none";
    
    modelTypeHelpIcon.addEventListener("click", () => {
        if (modelTypeHelp.style.display == "none") {
            modelTypeHelp.style.display = "block";
        } else {
            modelTypeHelp.style.display = "none";
        }
    });

    modelTypeGroup.appendChild(modelTypeLabel);
    modelTypeGroup.appendChild(modelTypeInput);
    modelTypeGroup.appendChild(modelTypeHelpIcon);


    // dependencies of node to add
    const modelPathGroup = document.createElement("div");
    modelPathGroup.className = "cs-input-group";
    
    const modelPathLabel = document.createElement("label");
    modelPathLabel.textContent = "Path:";
    modelPathLabel.className = "cs-label";
    
    const modelPathInput = document.createElement("input");
    modelPathInput.id = "add-model-path";
    modelPathInput.className = "cs-input";
    
    const modelPathHelpIcon = document.createElement("span");
    modelPathHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    modelPathHelpIcon.style.cursor = "pointer";
    modelPathHelpIcon.style.marginLeft = "5px";
    modelPathHelpIcon.title = "Click for help";
        
    const modelPathHelp = document.createElement("div");
    modelPathHelp.textContent = "Input the path of the model file (including file name, 'SD1.5/model.safetensors' = checkpoints/SD1.5/model.safetensors)";
    modelPathHelp.className = "cs-help-text";
    modelPathHelp.style.display = "none";
    
    modelPathHelpIcon.addEventListener("click", () => {
        if (modelPathHelp.style.display == "none") {
            modelPathHelp.style.display = "block";
        } else {
            modelPathHelp.style.display = "none";
        }
    });

    modelPathGroup.appendChild(modelPathLabel);
    modelPathGroup.appendChild(modelPathInput);
    modelPathGroup.appendChild(modelPathHelpIcon);
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.className = "cs-footer";
    
    const msgTxt = document.createElement("div");
    msgTxt.id = "comfystream-manage-models-add-msg-txt";
    msgTxt.style.fontSize = "0.75em";
    msgTxt.style.fontStyle = "italic";
    msgTxt.style.overflowWrap = "break-word";

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "cs-button";
    cancelButton.onclick = () => {
        modal.remove();
    };
    
    const addButton = document.createElement("button");
    addButton.textContent = "Add";
    addButton.className = "cs-button primary";
    addButton.onclick = async () => {
        const modelUrl = modelUrlInput.value;
        const modelType = modelTypeInput.value;
        const modelPath = modelPathInput.value;
        const payload = {
            url: modelUrl,
            type: modelType,
            path: modelPath
        };
        
        try {
            await settingsManager.manageComfystream( 
                "models", 
                "add",
                [payload]
            );
            msgTxt.textContent = "Model added successfully";
        } catch (error) {
            console.error("[ComfyStream] Error adding model:", error);
            msgTxt.textContent = error;
        }
    };

    footer.appendChild(msgTxt);
    footer.appendChild(cancelButton);
    footer.appendChild(addButton);
    
    // Assemble the modal
    form.appendChild(modelUrlGroup);
    form.appendChild(modelUrlHelp);
    form.appendChild(modelTypeGroup);
    form.appendChild(modelTypeHelp);
    form.appendChild(modelPathGroup);
    form.appendChild(modelPathHelp);

    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
}

async function showDeleteModelsModal() {
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-delete-model-modal");
    if (existingModal) {
        existingModal.remove();
    }    

    // Create nodes mgmt modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-delete-model-modal";
    modal.className = "comfystream-settings-modal";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.className = "cs-close-button";
    closeButton.onclick = () => {
        modal.remove();
    };

    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.className = "cs-modal-content";
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "Delete Model";
    title.className = "cs-title";
    
    // Create settings form
    const form = document.createElement("div");
        
    const msgTxt = document.createElement("div");
    msgTxt.id = "comfystream-manage-models-delete-msg-txt";
    msgTxt.style.fontSize = "0.75em";
    msgTxt.style.fontStyle = "italic";
    msgTxt.style.overflowWrap = "break-word";

    //Get the nodes
    const modelSelect = document.createElement("select");
    modelSelect.id = "comfystream-selected-model";
    try {
        const models = await settingsManager.manageComfystream(
            "models", 
            "list",
            ""
        );
        for (const model_type in models.models) {
            for (const model of models.models[model_type]) {
                const modelItem = document.createElement("option");
                modelItem.setAttribute("model-type", model.type);
                modelItem.value = model.path;
                modelItem.textContent = model.type + " | " + model.path;
                modelSelect.appendChild(modelItem);
            }            
        }
    } catch (error) {
        msgTxt.textContent = error;
    }
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.className = "cs-footer";
    

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "cs-button";
    cancelButton.onclick = () => {
        modal.remove();
    };
    
    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Delete";
    deleteButton.className = "cs-button primary";
    deleteButton.onclick = async () => {
        const modelPath = modelSelect.options[modelSelect.selectedIndex].value;
        const modelType = modelSelect.options[modelSelect.selectedIndex].getAttribute("model-type");
        const payload = {
            type: modelType,
            path: modelPath
        };
        
        try {
            await settingsManager.manageComfystream( 
                "models", 
                "delete",
                [payload]
            );
            msgTxt.textContent = "Model deleted successfully";
        } catch (error) {
            console.error("[ComfyStream] Error deleting model:", error);
            msgTxt.textContent = error;
        }
        
         
    };

    footer.appendChild(msgTxt);
    footer.appendChild(cancelButton);
    footer.appendChild(deleteButton);
    
    // Assemble the modal
    form.appendChild(modelSelect);

    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
}

async function showToggleNodesModal() {
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-toggle-nodes-modal");
    if (existingModal) {
        existingModal.remove();
    }    

    // Create nodes mgmt modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-toggle-nodes-modal";
    modal.className = "comfystream-settings-modal";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.className = "cs-close-button";
    closeButton.onclick = () => {
        modal.remove();
    };

    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.className = "cs-modal-content";
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "Enable/Disable Custom Nodes";
    title.className = "cs-title";
    
    // Create settings form
    const form = document.createElement("div");
    const toggleNodesModalContent = document.createElement("div");
    toggleNodesModalContent.className = "cs-modal-content";
    
    const msgTxt = document.createElement("div");
    msgTxt.id = "comfystream-manage-nodes-toggle-msg-txt";
    msgTxt.style.fontSize = "0.75em";
    msgTxt.style.fontStyle = "italic";
    msgTxt.style.overflowWrap = "break-word";

    //Get the nodes
    const nodeSelect = document.createElement("select");
    let initialAction = "Enable";
    nodeSelect.id = "comfystream-selected-node";
    try {
        const nodes = await settingsManager.manageComfystream(
            "nodes", 
            "list",
            ""
        );
        for (const node of nodes.nodes) {
            const nodeItem = document.createElement("option");
            nodeItem.value = node.name;
            nodeItem.textContent = node.name;
            nodeItem.setAttribute("node-is-disabled", node.disabled);
            if (!node.disabled) {
                initialAction = "Disable";
            }
            nodeSelect.appendChild(nodeItem);
        }
    } catch (error) {
        msgTxt.textContent = error;
    }
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.className = "cs-footer";
    

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "cs-button";
    cancelButton.onclick = () => {
        modal.remove();
    };
    
    const toggleButton = document.createElement("button");
    toggleButton.textContent = initialAction;
    toggleButton.className = "cs-button primary";
    toggleButton.onclick = async () => {
        const nodeName = nodeSelect.options[nodeSelect.selectedIndex].value;
        const payload = {
            name: nodeName,
        };
        const action = toggleButton.textContent === "Enable" ? "enable" : "disable";
        
        try {
            await settingsManager.manageComfystream( 
                "nodes", 
                "toggle",
                [payload]
            );
            msgTxt.textContent = `Node ${action} successfully`;
        } catch (error) {

        }
        
         
    };

    //update the action based on if the node is disabled or not currently
    nodeSelect.onchange = () => {
        const selectedNode = nodeSelect.options[nodeSelect.selectedIndex];
        const isDisabled = selectedNode.getAttribute("node-is-disabled") === "true";
        if (isDisabled) {
            toggleButton.textContent = "Enable";    
        } else {
            toggleButton.textContent = "Disable";
        }
    };

    footer.appendChild(msgTxt);
    footer.appendChild(cancelButton);
    footer.appendChild(toggleButton);
    
    // Assemble the modal
    form.appendChild(nodeSelect);

    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
}

async function showDeleteNodesModal() {
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-delete-nodes-modal");
    if (existingModal) {
        existingModal.remove();
    }    

    // Create nodes mgmt modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-delete-nodes-modal";
    modal.className = "comfystream-settings-modal";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.className = "cs-close-button";
    closeButton.onclick = () => {
        modal.remove();
    };

    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.className = "cs-modal-content";
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "Delete Custom Nodes";
    title.className = "cs-title";
    
    // Create settings form
    const form = document.createElement("div");
        
    const msgTxt = document.createElement("div");
    msgTxt.id = "comfystream-manage-nodes-delete-msg-txt";
    msgTxt.style.fontSize = "0.75em";
    msgTxt.style.fontStyle = "italic";
    msgTxt.style.overflowWrap = "break-word";

    //Get the nodes
    const nodeSelect = document.createElement("select");
    nodeSelect.id = "comfystream-selected-node";
    try {
        const nodes = await settingsManager.manageComfystream(
            "nodes", 
            "list",
            ""
        );
        for (const node of nodes.nodes) {
            const nodeItem = document.createElement("option");
            nodeItem.value = node.name;
            nodeItem.textContent = node.name;
            nodeSelect.appendChild(nodeItem);
        }
    } catch (error) {
        msgTxt.textContent = error;
    }
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.className = "cs-footer";
    

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "cs-button";
    cancelButton.onclick = () => {
        modal.remove();
    };
    
    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Delete";
    deleteButton.className = "cs-button primary";
    deleteButton.onclick = async () => {
        const nodeName = nodeSelect.options[nodeSelect.selectedIndex].value;
        const payload = {
            name: nodeName,
        };
        
        try {
            await settingsManager.manageComfystream( 
                "nodes", 
                "delete",
                [payload]
            );
            msgTxt.textContent = "Node deleted successfully";
        } catch (error) {
            console.error("[ComfyStream] Error deleting node:", error);
            msgTxt.textContent = error;
        }
        
         
    };

    footer.appendChild(msgTxt);
    footer.appendChild(cancelButton);
    footer.appendChild(deleteButton);
    
    // Assemble the modal
    form.appendChild(nodeSelect);

    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
}

async function showUpdateNodesModal() {
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-update-nodes-modal");
    if (existingModal) {
        existingModal.remove();
    }    

    // Create nodes mgmt modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-update-nodes-modal";
    modal.className = "comfystream-settings-modal";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.className = "cs-close-button";
    closeButton.onclick = () => {
        modal.remove();
    };

    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.className = "cs-modal-content";
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "Update Custom Nodes";
    title.className = "cs-title";
    
    // Create settings form
    const form = document.createElement("div");
        
    const msgTxt = document.createElement("div");
    msgTxt.id = "comfystream-manage-nodes-update-msg-txt";
    msgTxt.style.fontSize = "0.75em";
    msgTxt.style.fontStyle = "italic";
    msgTxt.style.overflowWrap = "break-word";

    //Get the nodes
    const nodeSelect = document.createElement("select");
    nodeSelect.id = "comfystream-selected-node";
    try {
        const nodes = await settingsManager.manageComfystream(
            "nodes", 
            "list",
            ""
        );
        let updateAvailable = false;
        for (const node of nodes.nodes) {
            if (node.update_available && node.update_available != "unknown" && node.url != "unknown") {
                updateAvailable = true;
                const nodeItem = document.createElement("option");
                nodeItem.value = node.url;
                nodeItem.textContent = node.name;
                nodeSelect.appendChild(nodeItem);
            }
        }
        if (!updateAvailable) {
            msgTxt.textContent = "No updates available for any nodes.";
        }
    } catch (error) {
        msgTxt.textContent = error;
    }
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.className = "cs-footer";
    

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "cs-button";
    cancelButton.onclick = () => {
        modal.remove();
    };
    
    const installButton = document.createElement("button");
    installButton.textContent = "Update";
    installButton.className = "cs-button primary";
    installButton.onclick = async () => {
        const nodeUrl = nodeSelect.options[nodeSelect.selectedIndex].value;
        const payload = {
            url: nodeUrl,
        };
        
        try {
            await settingsManager.manageComfystream( 
                "nodes", 
                "install",
                [payload]
            );
            msgTxt.textContent = "Node updated successfully";
        } catch (error) {
            console.error("[ComfyStream] Error updating node:", error);
            msgTxt.textContent = error;
        }
        
         
    };

    footer.appendChild(msgTxt);
    footer.appendChild(cancelButton);
    footer.appendChild(installButton);
    
    // Assemble the modal
    form.appendChild(nodeSelect);

    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
}

async function showInstallNodesModal() {
    // Check if modal already exists and remove it
    const existingModal = document.getElementById("comfystream-settings-add-nodes-modal");
    if (existingModal) {
        existingModal.remove();
    }    

    // Create nodes mgmt modal container
    const modal = document.createElement("div");
    modal.id = "comfystream-settings-add-nodes-modal";
    modal.className = "comfystream-settings-modal";
    
    // Create close button
    const closeButton = document.createElement("button");
    closeButton.textContent = "×";
    closeButton.className = "cs-close-button";
    closeButton.onclick = () => {
        modal.remove();
    };

    // Create modal content
    const modalContent = document.createElement("div");
    modalContent.className = "cs-modal-content";
    
    // Create title
    const title = document.createElement("h3");
    title.textContent = "Add Custom Nodes";
    title.className = "cs-title";
    
    // Create settings form
    const form = document.createElement("div");

    // URL of node to add
    const nodeUrlGroup = document.createElement("div");
    nodeUrlGroup.className = "cs-input-group";
    
    const nodeUrlLabel = document.createElement("label");
    nodeUrlLabel.textContent = "Url:";
    nodeUrlLabel.className = "cs-label";
    
    const nodeUrlInput = document.createElement("input");
    nodeUrlInput.id = "add-node-url";
    nodeUrlInput.className = "cs-input";
    
    
    const nodeUrlHelpIcon = document.createElement("span");
    nodeUrlHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    nodeUrlHelpIcon.style.cursor = "pointer";
    nodeUrlHelpIcon.style.marginLeft = "5px";
    nodeUrlHelpIcon.title = "Click for help";
    
    const nodeUrlHelp = document.createElement("div");
    nodeUrlHelp.textContent = "Specify the url of the github repo for the custom node want to install (can have .git at end of url)";
    nodeUrlHelp.className = "cs-help-text";
    nodeUrlHelp.style.display = "none";

    nodeUrlHelpIcon.addEventListener("click", () => {
        if (nodeUrlHelp.style.display == "none") {
            nodeUrlHelp.style.display = "block";
        } else {
            nodeUrlHelp.style.display = "none";
        }
    });

    nodeUrlGroup.appendChild(nodeUrlLabel);
    nodeUrlGroup.appendChild(nodeUrlInput);
    nodeUrlGroup.appendChild(nodeUrlHelpIcon);
    
    // branch of node to add
    const nodeBranchGroup = document.createElement("div");
    nodeBranchGroup.className = "cs-input-group";
    
    const nodeBranchLabel = document.createElement("label");
    nodeBranchLabel.textContent = "Branch:";
    nodeBranchLabel.className = "cs-label";
    
    const nodeBranchInput = document.createElement("input");
    nodeBranchInput.id = "add-node-branch";
    nodeBranchInput.className = "cs-input";
    
    const nodeBranchHelpIcon = document.createElement("span");
    nodeBranchHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    nodeBranchHelpIcon.style.cursor = "pointer";
    nodeBranchHelpIcon.style.marginLeft = "5px";
    nodeBranchHelpIcon.title = "Click for help";
    nodeBranchHelpIcon.style.position = "relative";

    const nodeBranchHelp = document.createElement("div");
    nodeBranchHelp.textContent = "Specify the branch of the node you want to add. For example, 'main' or 'develop'.";
    nodeBranchHelp.className = "cs-help-text";
    nodeBranchHelp.style.display = "none";
    
    nodeBranchHelpIcon.addEventListener("click", () => {
        if (nodeBranchHelp.style.display == "none") {
            nodeBranchHelp.style.display = "block";
        } else {
            nodeBranchHelp.style.display = "none";
        }
    });

    nodeBranchGroup.appendChild(nodeBranchLabel);
    nodeBranchGroup.appendChild(nodeBranchInput);
    nodeBranchGroup.appendChild(nodeBranchHelpIcon);


    // dependencies of node to add
    const nodeDepsGroup = document.createElement("div");
    nodeDepsGroup.className = "cs-input-group";
    
    const nodeDepsLabel = document.createElement("label");
    nodeDepsLabel.textContent = "Deps:";
    nodeDepsLabel.className = "cs-label";
    
    const nodeDepsInput = document.createElement("input");
    nodeDepsInput.id = "add-node-deps";
    nodeDepsInput.className = "cs-input";
    
    const nodeDepsHelpIcon = document.createElement("span");
    nodeDepsHelpIcon.innerHTML = "&#x1F6C8;"; // Unicode for a help icon (ℹ️)
    nodeDepsHelpIcon.style.cursor = "pointer";
    nodeDepsHelpIcon.style.marginLeft = "5px";
    nodeDepsHelpIcon.title = "Click for help";
        
    const nodeDepsHelp = document.createElement("div");
    nodeDepsHelp.textContent = "Comma separated list of python packages to install with pip (required packages outside requirements.txt)";
    nodeDepsHelp.className = "cs-help-text";
    nodeDepsHelp.style.display = "none";
    
    nodeDepsHelpIcon.addEventListener("click", () => {
        if (nodeDepsHelp.style.display == "none") {
            nodeDepsHelp.style.display = "block";
        } else {
            nodeDepsHelp.style.display = "none";
        }
    });

    nodeDepsGroup.appendChild(nodeDepsLabel);
    nodeDepsGroup.appendChild(nodeDepsInput);
    nodeDepsGroup.appendChild(nodeDepsHelpIcon);
    
    // Footer with buttons
    const footer = document.createElement("div");
    footer.className = "cs-footer";
    
    const msgTxt = document.createElement("div");
    msgTxt.id = "comfystream-manage-nodes-install-msg-txt";
    msgTxt.style.fontSize = "0.75em";
    msgTxt.style.fontStyle = "italic";
    msgTxt.style.overflowWrap = "break-word";

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "cs-button";
    cancelButton.onclick = () => {
        modal.remove();
    };
    
    const installButton = document.createElement("button");
    installButton.textContent = "Install";
    installButton.className = "cs-button primary";
    installButton.onclick = async () => {
        const nodeUrl = nodeUrlInput.value;
        const nodeBranch = nodeBranchInput.value;
        const nodeDeps = nodeDepsInput.value;
        const payload = {
            url: nodeUrl,
            branch: nodeBranch,
            dependencies: nodeDeps
        };
        
        try {
            await settingsManager.manageComfystream( 
                "nodes", 
                "install",
                [payload]
            );
            msgTxt.textContent = "Node installed successfully!";
        } catch (error) {
            console.error("[ComfyStream] Error installing node:", error);
            msgTxt.textContent = error;
        }
        
         
    };

    footer.appendChild(msgTxt);
    footer.appendChild(cancelButton);
    footer.appendChild(installButton);
    
    // Assemble the modal
    form.appendChild(nodeUrlGroup);
    form.appendChild(nodeUrlHelp);
    form.appendChild(nodeBranchGroup);
    form.appendChild(nodeBranchHelp);
    form.appendChild(nodeDepsGroup);
    form.appendChild(nodeDepsHelp);

    modalContent.appendChild(closeButton);
    modalContent.appendChild(title);
    modalContent.appendChild(form);
    modalContent.appendChild(footer);
    
    modal.appendChild(modalContent);
    
    // Add to document
    document.body.appendChild(modal);
}
// Export for use in other modules
export { settingsManager, showSettingsModal, showInstallNodesModal, showUpdateNodesModal, showDeleteNodesModal, showToggleNodesModal, showAddModelsModal, showDeleteModelsModal, showSetTurnServerCredsModal };

// Also keep the global for backward compatibility
window.comfyStreamSettings = {
    settingsManager,
    showSettingsModal,
    showInstallNodesModal,
    showUpdateNodesModal,
    showDeleteNodesModal,
    showToggleNodesModal,
    showAddModelsModal,
    showDeleteModelsModal,
    showSetTurnServerCredsModal
}; 