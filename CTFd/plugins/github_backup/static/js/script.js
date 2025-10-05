




// const githubReposList = document.getElementById("github-repos-list");
// const githubRepoSearch = document.getElementById("github-repo-search");
// const githubRepoPagination = document.getElementById("github-repo-pagination");
















  // function importRepoById(repoId, row) {
  //   const syncCell = row.querySelector("td:nth-child(3)");
  //   const deleteBtn = row.querySelector(".delete-repo-btn");
  //   const btn = row.querySelector(".sync-now-btn");
  //   const originalSyncContent = syncCell.innerHTML;
  //
  //   syncCell.innerHTML = `
  //   <div class="text-center">
  //     <i class="fas fa-spinner fa-spin text-warning"></i>
  //     <div class="small text-muted">Importing...</div>
  //   </div>
  // `;
  //
  //   btn.disabled = true;
  //   deleteBtn.disabled = true;
  //
  //
  //   fetch(`/plugins/github_backup/repos/${repoId}/import`, {
  //       method: "POST",
  //       credentials: "same-origin",
  //       headers: {
  //         "Content-Type": "application/json",
  //         "CSRF-Token": CTFd.config.csrfNonce
  //       },
  //       body: JSON.stringify({})
  //   })
  //     .then((r) => r.json())
  //     .then((resp) => {
  //       if (resp.success) {
  //         let body = `<p>${resp.message}</p>`;
  //         if (resp.errors?.length) {
  //           body += "<hr><b>Errors during import:</b><ul>";
  //           resp.errors.forEach((err) => {
  //             body += `<li><code>${err.file}</code>: ${err.error}</li>`;
  //           });
  //           body += "</ul>";
  //         }
  //         alert("Import complete.\n" + body);
  //         loadSavedRepos();
  //       } else {
  //         alert("Error: " + resp.message);
  //         syncCell.innerHTML = originalSyncContent;
  //       }
  //     })
  //     .catch((err) => {
  //       alert("Unexpected Error: " + err.message);
  //       syncCell.innerHTML = originalSyncContent;
  //     })
  //     .finally(() => {
  //       btn.disabled = false;
  //       deleteBtn.disabled = false;
  //     });
  // }




