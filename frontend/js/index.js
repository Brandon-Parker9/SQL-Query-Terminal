const sqlEditor = document.getElementById('sql-editor');
const queriesList = document.getElementById('saved-queries-list');
const queryNameInput = document.getElementById('new-query-name');

// -- API Interaction Functions --

// Function to load saved queries from the backend and render them in the sidebar
async function loadSavedQueries() {
    try {
        const response = await fetch(`/api/queries`);
        const data = await response.json();
        // Clear the current list and render the new data
        savedQueries = data; 
        renderQueries();
    } catch (err) {
        console.error("Could not connect to Python backend:", err);
    }
}

// Function to add a new saved query to the database
async function addSavedQuery() {
    const name = queryNameInput.value.trim();
    const sql = sqlEditor.value.trim();

    if (!name || !sql || sql === "-- Select a saved query or type here...") {
        alert("Please enter a name and valid SQL code.");
        return;
    }

    try {
        const response = await fetch(`/api/queries`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, sql })
        });

        const result = await response.json();

        if (response.ok) {
            queryNameInput.value = "";
            alert("Query saved successfully!");
            loadSavedQueries(); 
        } else {
            // 2. This now shows the EXACT error from Pydantic
            alert("Failed to save: " + (result.detail || "Unknown error"));
        }
    } catch (err) {
        console.error("Error saving query:", err);
    }
}

// Function to delete a saved query from the database
async function deleteSavedQuery(id) {
    if (confirm("Are you sure you want to delete this saved query?")) {
        try {
            const response = await fetch(`/api/queries/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                loadSavedQueries(); // Refresh the list
            } else {
                alert("Failed to delete query.");
            }
        } catch (err) {
            console.error("Error deleting query:", err);
        }
    }
}

// Function to execute the SQL query and display results
async function executeQuery() {
    const sql = document.getElementById('sql-editor').value;
    const btn = document.getElementById('btn-execute');
    const resultsContainer = document.getElementById('results-container');
    
    // 1. Visual feedback
    btn.innerText = "Running...";
    resultsContainer.innerHTML = '<p class="text-zinc-400 animate-pulse font-mono">Executing query on server...</p>';
    
    try {
        const response = await fetch(`/api/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql: sql })
        });
        const result = await response.json();
        
        // 2. Check if the backend returned an error message
        if (response.status !== 200) {
            resultsContainer.innerHTML = `<p class="text-red-600 font-mono text-sm p-4">Error: ${result.detail}</p>`;
            return;
        }

        // 3. Render the data into the table (No more alert pop-up!)
        renderTable(result.data);
        
    } catch (err) {
        resultsContainer.innerHTML = `<p class="text-red-600 font-mono text-sm p-4">Connection Failed: ${err.message}</p>`;
    } finally {
        btn.innerHTML = '<span class="material-symbols-outlined text-base">play_arrow</span> Execute Query';
    }
}

// Function to export the current SQL query results as an Excel file
async function downloadExcel() {
    const sql = document.getElementById('sql-editor').value;
    const btn = document.getElementById('btn-export');
    
    // Visual feedback
    const originalContent = btn.innerHTML;
    btn.innerText = "Generating...";

    try {
        const response = await fetch(`/api/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql: sql })
        });

        if (response.status !== 200) {
            const error = await response.json();
            alert("Export failed: " + error.detail);
            return;
        }

        // Convert the response to a "Blob" (Binary Large Object)
        const blob = await response.blob();
        
        // Create a temporary link to trigger the download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        // This creates a format like: Business_Insights_2026-03-20_22-07-57.xlsx
        const timestamp = new Date().toISOString().replace(/T/, '_').replace(/:/g, '-').split('.')[0];
        a.download = `Business_Insights_${timestamp}.xlsx`;
                    
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

    } catch (err) {
        alert("Export connection error: " + err.message);
    } finally {
        btn.innerHTML = originalContent;
    }
}

// -- UI Interaction Functions --

// Function to paste query into the editor when a saved query is clicked
function pasteQuery(sql) {
    sqlEditor.value = sql;
    sqlEditor.classList.add('bg-yellow-50');
    setTimeout(() => sqlEditor.classList.remove('bg-yellow-50'), 300);
}

// Helper function to build the HTML table dynamically
function renderTable(data) {
    const container = document.getElementById('results-container');
    
    if (!data || data.length === 0) {
        container.innerHTML = '<p class="text-zinc-400 italic text-sm p-8">Query returned 0 rows.</p>';
        return;
    }

    // Get headers from the first object keys
    const headers = Object.keys(data[0]);
    
    let html = `
        <table class="w-full text-left border-collapse">
            <thead class="bg-zinc-100 border-b-2 border-zinc-200">
                <tr>
                    ${headers.map(h => `<th class="px-4 py-2 text-[10px] font-black uppercase tracking-widest text-zinc-600">${h}</th>`).join('')}
                </tr>
            </thead>
            <tbody class="divide-y divide-zinc-100">
                ${data.map(row => `
                    <tr class="hover:bg-zinc-50 transition-colors">
                        ${headers.map(h => `<td class="px-4 py-3 text-sm font-mono text-zinc-700">${row[h] !== null ? row[h] : '<span class="text-zinc-300">NULL</span>'}</td>`).join('')}
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

// Helper function to render the saved queries in the sidebar
function renderQueries() {
    queriesList.innerHTML = '';
    savedQueries.forEach(q => {
        const div = document.createElement('div');
        div.className = "group flex items-center border-b border-zinc-200/50 hover:bg-zinc-300 transition-colors";
        
        div.innerHTML = `
            <button onclick="pasteQuery(\`${q.sql}\`)" class="flex-1 text-left px-6 py-3 text-xs font-bold uppercase flex justify-between items-center">
                <span>${q.name}</span>
            </button>
            <button onclick="deleteSavedQuery(${q.id})" class="px-4 py-3 text-zinc-400 hover:text-primary opacity-0 group-hover:opacity-100 transition-all" title="Delete Query">
                <span class="material-symbols-outlined text-sm">delete</span>
            </button>
        `;
        queriesList.appendChild(div);
    });
}

// Attach the function to the save query button
document.getElementById('btn-save-query').onclick = addSavedQuery;

// Attach the function to your button
document.getElementById('btn-execute').onclick = executeQuery;

// Attach the function to the export button
document.getElementById('btn-export').onclick = downloadExcel;

// Run load on start
window.onload = loadSavedQueries;