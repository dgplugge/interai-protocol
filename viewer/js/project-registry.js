/**
 * AICP Project Registry Service
 * Loads, validates, and manages the project registry for consistent
 * project identity across Builder, Viewer, and future .NET services.
 *
 * Protocol: AICP/1.0
 * Slice 9 — Project Registry
 */

var projectRegistry = [];
var projectRegistryLoaded = false;

/**
 * Load the project registry from the server API or local file fallback.
 * @returns {Promise<Array>} The loaded project list
 */
async function loadProjectRegistry() {
    try {
        var response = await fetch('/api/project-registry');
        if (response.ok) {
            var data = await response.json();
            projectRegistry = data.projects || [];
            projectRegistryLoaded = true;
            console.log('[ProjectRegistry] Loaded ' + projectRegistry.length + ' project(s) from API');
            return projectRegistry;
        }
    } catch (e) {
        console.warn('[ProjectRegistry] API fetch failed, trying local file:', e.message);
    }

    // Fallback: try loading the JSON file directly
    try {
        var response2 = await fetch('project-registry.json');
        if (response2.ok) {
            var data2 = await response2.json();
            projectRegistry = data2.projects || [];
            projectRegistryLoaded = true;
            console.log('[ProjectRegistry] Loaded ' + projectRegistry.length + ' project(s) from local file');
            return projectRegistry;
        }
    } catch (e2) {
        console.warn('[ProjectRegistry] Local file fallback failed:', e2.message);
    }

    projectRegistry = [];
    projectRegistryLoaded = true;
    return projectRegistry;
}

/**
 * Get all projects from the registry.
 * @returns {Array} List of project objects
 */
function getAllRegistryProjects() {
    return projectRegistry;
}

/**
 * Look up a project by its ID.
 * @param {string} id - The projectId to find
 * @returns {Object|null} The project object or null
 */
function getRegistryProjectById(id) {
    if (!id) return null;
    for (var i = 0; i < projectRegistry.length; i++) {
        if (projectRegistry[i].projectId === id) return projectRegistry[i];
    }
    return null;
}

/**
 * Get the domain for a project ID from the registry.
 * Replaces the hardcoded getDomainForProject() in builder.js.
 * @param {string} projectId
 * @returns {string} The domain or empty string
 */
function getRegistryDomain(projectId) {
    var proj = getRegistryProjectById(projectId);
    return proj ? proj.domain : '';
}

/**
 * Get the message ID prefix for a project.
 * Example: "OperatorHub" -> "OH-MSG-"
 * Falls back to "MSG-" for legacy projects.
 * @param {string} projectId
 * @returns {string}
 */
function getRegistryMessagePrefix(projectId) {
    var proj = getRegistryProjectById(projectId);
    return (proj && proj.messagePrefix) ? proj.messagePrefix : 'MSG-';
}

/**
 * Get the default recipient list for a project.
 * @param {string} projectId
 * @param {string} [sender] Optional sender to exclude from recipients
 * @returns {string[]} Recipient names
 */
function getRegistryDefaultRecipients(projectId, sender) {
    var proj = getRegistryProjectById(projectId);
    if (!proj || !Array.isArray(proj.defaultAgents)) return [];
    var senderLower = (sender || '').toLowerCase().trim();
    return proj.defaultAgents.filter(function(agent) {
        return agent && agent.toLowerCase() !== senderLower;
    });
}

/**
 * Normalize a project name into a machine-readable ID.
 * "Study Guide" -> "StudyGuide", "My Cool Project" -> "MyCoolProject"
 * @param {string} name
 * @returns {string}
 */
function normalizeProjectId(name) {
    return name.replace(/[^a-zA-Z0-9]+/g, ' ')
               .trim()
               .split(/\s+/)
               .map(function(word) {
                   return word.charAt(0).toUpperCase() + word.slice(1);
               })
               .join('');
}

/**
 * Validate a project object before saving.
 * @param {Object} project - The project to validate
 * @returns {{ valid: boolean, errors: string[] }}
 */
function validateRegistryProject(project) {
    var errors = [];

    if (!project.projectName || !project.projectName.trim()) {
        errors.push('Project name is required');
    }
    if (!project.domain || !project.domain.trim()) {
        errors.push('Domain is required');
    }

    // Generate ID from name if not provided
    if (!project.projectId && project.projectName) {
        project.projectId = normalizeProjectId(project.projectName);
    }

    if (!project.projectId) {
        errors.push('Project ID could not be generated');
    }

    // Check for duplicate ID
    for (var i = 0; i < projectRegistry.length; i++) {
        if (projectRegistry[i].projectId === project.projectId) {
            errors.push('A project with ID "' + project.projectId + '" already exists');
            break;
        }
    }

    // Check for duplicate name (case-insensitive)
    var nameLower = (project.projectName || '').toLowerCase().trim();
    for (var j = 0; j < projectRegistry.length; j++) {
        if (projectRegistry[j].projectName.toLowerCase().trim() === nameLower) {
            errors.push('A project with name "' + project.projectName + '" already exists');
            break;
        }
    }

    return { valid: errors.length === 0, errors: errors };
}

/**
 * Save a new project to the registry via the server API.
 * Also adds it to the local in-memory array.
 * @param {Object} project - The project to save
 * @returns {Promise<{ok: boolean, error?: string}>}
 */
async function saveRegistryProject(project) {
    // Ensure defaults
    if (!project.projectId) {
        project.projectId = normalizeProjectId(project.projectName);
    }
    if (!project.status) project.status = 'incubating';
    if (!project.createdOn) project.createdOn = new Date().toISOString();
    if (!project.defaultAgents) project.defaultAgents = [];
    if (!project.tags) project.tags = [];
    if (!project.description) project.description = '';

    var validation = validateRegistryProject(project);
    if (!validation.valid) {
        return { ok: false, error: validation.errors.join('; ') };
    }

    try {
        var response = await fetch('/api/project-registry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(project)
        });
        var result = await response.json();

        if (result.ok) {
            // Add to local registry
            projectRegistry.push(project);
            return { ok: true };
        } else {
            return { ok: false, error: result.error || 'Server error' };
        }
    } catch (e) {
        return { ok: false, error: 'Network error: ' + e.message };
    }
}

/**
 * Populate a <select> element with projects from the registry.
 * Adds a "+ New Project" option at the end.
 * @param {string} selectId - The ID of the select element
 * @param {string} [selectedId] - Optional project ID to pre-select
 */
function populateProjectDropdown(selectId, selectedId) {
    var select = document.getElementById(selectId);
    if (!select) return;

    // Clear existing options
    select.innerHTML = '';

    // Add project options
    for (var i = 0; i < projectRegistry.length; i++) {
        var proj = projectRegistry[i];
        var opt = document.createElement('option');
        opt.value = proj.projectId;
        opt.textContent = proj.projectName;
        if (proj.status !== 'active') {
            opt.textContent += ' (' + proj.status + ')';
        }
        select.appendChild(opt);
    }

    // Add separator and "New Project" option
    var sep = document.createElement('option');
    sep.disabled = true;
    sep.textContent = '────────────';
    select.appendChild(sep);

    var newOpt = document.createElement('option');
    newOpt.value = '__new__';
    newOpt.textContent = '+ New Project';
    select.appendChild(newOpt);

    // Set selected value
    if (selectedId && getRegistryProjectById(selectedId)) {
        select.value = selectedId;
    } else if (projectRegistry.length > 0) {
        select.value = projectRegistry[0].projectId;
    }
}
