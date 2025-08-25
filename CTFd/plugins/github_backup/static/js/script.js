
const ITEMS_PER_PAGE = 10;
let allRepos = [];
let currentPage = 1;

const githubLoginSection = document.getElementById("github-login-section");
const githubReposSection = document.getElementById("github-repos-section");
const githubReposList = document.getElementById("github-repos-list");
const githubRepoSearch = document.getElementById("github-repo-search");
const githubRepoPagination = document.getElementById("github-repo-pagination");

// Listeners
githubRepoSearch?.addEventListener("input", () => {
    currentPage = 1;
    renderRepos();
});

// Functions
function renderRepos() {
    const searchTerm = githubRepoSearch.value.toLowerCase();
    const filteredRepos = allRepos.filter(repo =>
        repo.full_name.toLowerCase().includes(searchTerm)
    );
    const totalPages = Math.ceil(filteredRepos.length / ITEMS_PER_PAGE);
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const reposToShow = filteredRepos.slice(start, end);

    githubReposList.innerHTML = "";
    reposToShow.forEach((repo, index) => {
        const id = `repo-${index}`;
        const div = document.createElement("div");
        div.className = "form-check";
        div.innerHTML = `
        <input class="form-check-input" type="checkbox" value="${repo.full_name}" id="${id}">
        <label class="form-check-label" for="${id}">${repo.full_name}</label>
        `;
        githubReposList.appendChild(div);
    });

    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    githubRepoPagination.innerHTML = "";

    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement("li");
        li.className = `page-item ${i === currentPage ? "active" : ""}`;
        li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        li.addEventListener("click", (e) => {
        e.preventDefault();
        currentPage = i;
        renderRepos();
        });
        githubRepoPagination.appendChild(li);
    }
}

function loadSavedRepos() {
    const tableBody = document.querySelector("#github-saved-repos-table tbody");
    tableBody.innerHTML = "";

    fetch("/api/v1/github/repos/saved", {
      method: "GET",
      credentials: "same-origin"
    })
      .then((response) => response.json())
      .then((data) => {
        if (!data.success) {
          throw new Error(data.message || "Could not load the repositories.");
        }

        const repos = data.repos;

        if (repos.length === 0) {
          const emptyRow = document.createElement("tr");
          const td = document.createElement("td");
          td.setAttribute("colspan", "4");
          td.classList.add("text-center", "text-muted");
          td.textContent = "No saved repositories.";
          emptyRow.appendChild(td);
          tableBody.appendChild(emptyRow);
          return;
        }

        // If there are repos, render them
        repos.forEach((repo) => {
          const tr = document.createElement("tr");

          // Checkbox column
          const checkboxTd = document.createElement("td");
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.className = "sync-checkbox";
          checkbox.value = repo.id;
          checkboxTd.appendChild(checkbox);

          const nameTd = document.createElement("td");
          nameTd.textContent = repo.full_name;

          const lastImportTd = document.createElement("td");
          lastImportTd.textContent = repo.last_synced_at ? `${repo.last_synced_at} UTC` : "-";

          const actionsTd = document.createElement("td");
          actionsTd.innerHTML = `
          <button class="btn btn-sm btn-warning sync-now-btn" data-id="${repo.id}">
            <i class="fas fa-download me-1"></i> ${repo.selected ? "Update" : "Import"}
          </button>
          <button class="btn btn-sm btn-danger delete-repo-btn" data-id="${repo.id}">
            <i class="fas fa-trash me-1"></i> Delete
          </button>
        `;

          tr.appendChild(checkboxTd);
          tr.appendChild(nameTd);
          tr.appendChild(lastImportTd);
          tr.appendChild(actionsTd);
          tableBody.appendChild(tr);
        });


        // Link actions
        document.querySelectorAll(".delete-repo-btn").forEach((btn) => {
          btn.addEventListener("click", () => {
            const repoId = btn.getAttribute("data-id");

            if (confirm("Are you sure you want to delete this repository?")) {
              fetch(`/api/v1/github/repos/${repoId}`, {
                method: "DELETE",
                credentials: "same-origin",
                headers: {
                  "CSRF-Token": CTFd.config.csrfNonce
                }
              })
                .then((r) => r.json())
                .then((resp) => {
                  if (resp.success) {
                    alert("Deleted: " + resp.message);
                    loadSavedRepos();
                  } else {
                    alert("Error: " + resp.message);
                  }
                });
            }
          });
        });


        document.querySelectorAll(".sync-now-btn").forEach((btn) => {
          btn.addEventListener("click", () => {
            const repoId = btn.getAttribute("data-id");

            if (confirm("Are you sure you want to import the challenges from this repository?")) {
              // Find related elements
              const row = btn.closest("tr");
              const syncCell = row.querySelector("td:nth-child(3)");
              const deleteBtn = row.querySelector(".delete-repo-btn");

              // Save the original content of the date cell
              const originalSyncContent = syncCell.innerHTML;

              // Replace with spinner
              syncCell.innerHTML = `
                <div class="text-center">
                  <i class="fas fa-spinner fa-spin text-warning"></i>
                  <div class="small text-muted">Importing...</div>
                </div>
              `;

              // Disable buttons
              btn.disabled = true;
              deleteBtn.disabled = true;

              fetch(`/api/v1/github/repos/${repoId}/import`, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                  "CSRF-Token": CTFd.config.csrfNonce
                }
              })
                .then((r) => r.json())
                .then((resp) => {
                  if (resp.success) {
                    let message = resp.message;
                    if (resp.errors && resp.errors.length > 0) {
                      message += "\n\nErrors during import:\n";
                      resp.errors.forEach((err) => {
                        message += `- ${err.file}: ${err.error}\n`;
                      });
                    }

                    alert("Import complete: " + message);

                    loadSavedRepos(); // Update the entire table
                  } else {
                    syncCell.innerHTML = originalSyncContent;
                    btn.disabled = false;
                    deleteBtn.disabled = false;

                    alert("Error: " + resp.message);
                  }
                })
                .catch((err) => {
                  syncCell.innerHTML = originalSyncContent;
                  btn.disabled = false;
                  deleteBtn.disabled = false;

                  alert("Unexpected Error: " + err.message);
                })
                .finally(() => {
                  // Always re-enable the buttons at the end
                  btn.disabled = false;
                  deleteBtn.disabled = false;
                  syncCell.innerHTML = originalSyncContent; // Restore original content
                });
            }
          });
        });

        document.getElementById("import-selected-repos")?.addEventListener("click", () => {
          const checkboxes = document.querySelectorAll(".sync-checkbox:checked");
          if (checkboxes.length === 0) {
            alert("No repositories selected.\nSelect at least one repository to import.");
            return;
          }

          if (confirm(`You will import ${checkboxes.length} repositories. Continue?`)) {
            checkboxes.forEach((cb) => {
              const repoId = cb.value;
              const row = cb.closest("tr");
              importRepoById(repoId, row);
            });
          }
        })
          })
          .catch((err) => {
            alert("Error: " + err.message);
          });
}

// Fetch blueprint
// Fetch repos desde la API
  fetch("/repos")
  .then(response => {
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Usuario no autenticado con GitHub. Por favor, instala la app o asegúrate de tener permisos.");
      }
      return response.json().then(err => {
        throw new Error(err.message || "Error inesperado al comunicarse con la API.");
      });
    }
    return response.json();
  })
  .then(data => {
    if (!data.success) {
      throw new Error(data.message + "hola" || "La API respondió sin éxito.");
    }

    allRepos = data.repos || [];

    // Asegúrate de mostrar y ocultar las secciones correctamente
    if (githubLoginSection) githubLoginSection.style.display = "none";
    if (githubReposSection) githubReposSection.style.display = "block";
    const errorSection = document.getElementById("github-error-section");
    if (errorSection) errorSection.style.display = "none";

    renderRepos();
    loadSavedRepos();
  })
  .catch(error => {
    console.error("Error al obtener los repos:", error);
    const errorSection = document.getElementById("github-error-section");
    const errorMessage = document.getElementById("github-error-message");
    if (errorMessage) errorMessage.textContent = error.message;
    if (errorSection) errorSection.style.display = "block";
    if (githubLoginSection) githubLoginSection.style.display = "block";
    if (githubReposSection) githubReposSection.style.display = "none";
  });

// Save selected repos
  document.getElementById("save-selected-repos")?.addEventListener("click", () => {
    const checkboxes = document.querySelectorAll("#github-repos-list input[type=checkbox]:checked");
    const selected = [];

    checkboxes.forEach(checkbox => {
      const repo = allRepos.find(r => r.full_name === checkbox.value);
      if (repo) {
        selected.push(repo);
      }
    });

    fetch("/api/v1/github/repos/selection", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "CSRF-Token": CTFd.config.csrfNonce
      },
      body: JSON.stringify({ repos: selected })
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert("Repositories saved successfully.");
        } else {
          alert("Error saving: " + data.message || "Unexpected error.");
        }
      })
        .catch(err => {
            alert("Unexpected Error: " + err.message);
      });
  });

  function importRepoById(repoId, row) {
    const syncCell = row.querySelector("td:nth-child(3)");
    const deleteBtn = row.querySelector(".delete-repo-btn");
    const btn = row.querySelector(".sync-now-btn");
    const originalSyncContent = syncCell.innerHTML;

    syncCell.innerHTML = `
    <div class="text-center">
      <i class="fas fa-spinner fa-spin text-warning"></i>
      <div class="small text-muted">Importing...</div>
    </div>
  `;

    btn.disabled = true;
    deleteBtn.disabled = true;


    fetch(`/api/v1/github/repos/${repoId}/import`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "CSRF-Token": CTFd.config.csrfNonce
      }
    })
      .then((r) => r.json())
      .then((resp) => {
        if (resp.success) {
          let body = `<p>${resp.message}</p>`;
          if (resp.errors?.length) {
            body += "<hr><b>Errors during import:</b><ul>";
            resp.errors.forEach((err) => {
              body += `<li><code>${err.file}</code>: ${err.error}</li>`;
            });
            body += "</ul>";
          }
          alert("Import complete.\n" + body);
          loadSavedRepos();
        } else {
          alert("Error: " + resp.message);
          syncCell.innerHTML = originalSyncContent;
        }
      })
      .catch((err) => {
        alert("Unexpected Error: " + err.message);
        syncCell.innerHTML = originalSyncContent;
      })
      .finally(() => {
        btn.disabled = false;
        deleteBtn.disabled = false;
      });
  }

  // Help Button Event Listener
  document.getElementById("help-button")?.addEventListener("click", () => {
    $('#help-modal').modal('show');
  });