document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const promptList = document.getElementById('prompt-list');
    const codeEditor = document.getElementById('code-editor');
    const currentFilename = document.getElementById('current-filename');
    const currentVersion = document.getElementById('current-version');
    const unsavedChangesBadge = document.getElementById('unsaved-changes');
    const saveBtn = document.getElementById('save-btn');
    const revertBtn = document.getElementById('revert-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const variablesList = document.getElementById('variables-list');
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');

    // State
    let currentPrompt = null;
    let originalContent = '';
    let isDirty = false;

    // Initialize
    loadPrompts();

    // Event Listeners
    refreshBtn.addEventListener('click', loadPrompts);
    
    codeEditor.addEventListener('input', () => {
        if (!currentPrompt) return;
        
        const newContent = codeEditor.value;
        if (newContent !== originalContent) {
            setDirty(true);
        } else {
            setDirty(false);
        }
    });

    saveBtn.addEventListener('click', async () => {
        if (!currentPrompt || !isDirty) return;
        await savePrompt();
    });

    revertBtn.addEventListener('click', () => {
        if (!currentPrompt) return;
        if (confirm('Are you sure you want to revert changes?')) {
            codeEditor.value = originalContent;
            setDirty(false);
        }
    });

    // Functions
    async function loadPrompts() {
        promptList.innerHTML = '<div class="loading-spinner-small"></div>';
        
        try {
            const response = await fetch('/api/prompts');
            const result = await response.json();
            
            if (result.success) {
                renderPromptList(result.data);
            } else {
                showToast('Failed to load prompts', 'error');
            }
        } catch (error) {
            console.error('Error loading prompts:', error);
            promptList.innerHTML = '<p class="text-muted" style="padding: 1rem;">Failed to load prompts.</p>';
        }
    }

    function renderPromptList(prompts) {
        promptList.innerHTML = '';
        
        if (prompts.length === 0) {
            promptList.innerHTML = '<p class="text-muted" style="padding: 1rem;">No prompts found.</p>';
            return;
        }

        prompts.forEach(prompt => {
            const item = document.createElement('div');
            item.className = 'prompt-item';
            if (currentPrompt && currentPrompt.filename === prompt.filename) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <span class="prompt-name">${prompt.name}</span>
                <div class="prompt-meta">
                    <span>${prompt.version ? 'v' + prompt.version : ''}</span>
                    <span>${formatDate(prompt.modified)}</span>
                </div>
            `;
            
            item.addEventListener('click', () => {
                if (isDirty) {
                    if (!confirm('You have unsaved changes. Discard them?')) {
                        return;
                    }
                }
                loadPromptContent(prompt.filename);
                
                // Update active state
                document.querySelectorAll('.prompt-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
            });
            
            promptList.appendChild(item);
        });
    }

    async function loadPromptContent(filename) {
        // Disable editor while loading
        codeEditor.disabled = true;
        codeEditor.value = 'Loading...';
        
        try {
            const response = await fetch(`/api/prompts/${filename}`);
            const result = await response.json();
            
            if (result.success) {
                currentPrompt = result.data;
                originalContent = result.data.content;
                
                // Update UI
                codeEditor.value = originalContent;
                codeEditor.disabled = false;
                currentFilename.textContent = result.data.name;
                
                // Extract version if present in YAML
                const versionMatch = originalContent.match(/semantic_version:\s*["']?([^"'\n]+)["']?/);
                if (versionMatch) {
                    currentVersion.textContent = 'v' + versionMatch[1];
                    currentVersion.classList.remove('hidden');
                } else {
                    currentVersion.classList.add('hidden');
                }
                
                setDirty(false);
                loadVariables(filename);
                
            } else {
                showToast('Failed to load prompt content', 'error');
                codeEditor.value = '';
            }
        } catch (error) {
            console.error('Error loading prompt content:', error);
            showToast('Error loading prompt content', 'error');
        }
    }

    async function loadVariables(filename) {
        variablesList.innerHTML = '<div class="loading-spinner-small"></div>';
        
        try {
            const response = await fetch(`/api/prompts/${filename}/variables`);
            const result = await response.json();
            
            if (result.success) {
                renderVariables(result.data.variables);
            } else {
                variablesList.innerHTML = '<p class="text-muted">Failed to load variables.</p>';
            }
        } catch (error) {
            console.error('Error loading variables:', error);
            variablesList.innerHTML = '<p class="text-muted">Error loading variables.</p>';
        }
    }

    function renderVariables(variables) {
        variablesList.innerHTML = '';
        
        if (!variables || variables.length === 0) {
            variablesList.innerHTML = '<p class="text-muted">No variables defined.</p>';
            return;
        }

        variables.forEach(variable => {
            const item = document.createElement('div');
            item.className = 'variable-item';
            
            const requiredBadge = variable.required ? '<span class="variable-required">Required</span>' : '';
            
            item.innerHTML = `
                <span class="variable-name">${variable.name}${requiredBadge}</span>
                <span class="variable-desc">${variable.description || 'No description'}</span>
                ${variable.default_value ? `<div class="text-muted" style="font-size: 0.75rem; margin-top: 0.25rem;">Default: ${variable.default_value}</div>` : ''}
            `;
            
            variablesList.appendChild(item);
        });
    }

    async function savePrompt() {
        if (!currentPrompt) return;
        
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
        
        try {
            const response = await fetch(`/api/prompts/${currentPrompt.filename}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: codeEditor.value
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                originalContent = codeEditor.value;
                setDirty(false);
                showToast('Prompt saved successfully', 'success');
                
                // Reload variables in case they changed
                loadVariables(currentPrompt.filename);
                
                // Refresh list to update modified time
                loadPrompts();
            } else {
                showToast(result.error || 'Failed to save prompt', 'error');
            }
        } catch (error) {
            console.error('Error saving prompt:', error);
            showToast('Error saving prompt', 'error');
        } finally {
            saveBtn.disabled = !isDirty; // Re-enable if still dirty (failed) or disable if clean (success)
            saveBtn.innerHTML = '<i class="fa-solid fa-save"></i> Save Changes';
            if (!isDirty) saveBtn.disabled = true;
        }
    }

    function setDirty(dirty) {
        isDirty = dirty;
        if (dirty) {
            unsavedChangesBadge.classList.remove('hidden');
            saveBtn.disabled = false;
            revertBtn.disabled = false;
        } else {
            unsavedChangesBadge.classList.add('hidden');
            saveBtn.disabled = true;
            revertBtn.disabled = true;
        }
    }

    function showToast(message, type = 'success') {
        toastMessage.textContent = message;
        toast.classList.remove('hidden');
        
        // Auto hide
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    }

    function formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
});
