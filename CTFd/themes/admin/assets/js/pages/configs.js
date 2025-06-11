import "./main";
import "bootstrap/js/dist/tab";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import timezones from "../timezones";
import CTFd from "../compat/CTFd";
import { default as helpers } from "../compat/helpers";
import $ from "jquery";
import "../compat/json";
import { ezQuery, ezProgressBar, ezAlert } from "../compat/ezq";
import CodeMirror from "codemirror";
import "codemirror/mode/htmlmixed/htmlmixed.js";
import Vue from "vue";
import FieldList from "../components/configs/fields/FieldList.vue";
import BracketList from "../components/configs/brackets/BracketList.vue";

dayjs.extend(advancedFormat);
dayjs.extend(utc);
dayjs.extend(timezone);

function loadTimestamp(place, timestamp) {
  if (typeof timestamp == "string") {
    timestamp = parseInt(timestamp, 10) * 1000;
  }
  const d = dayjs(timestamp);
  $("#" + place + "-month").val(d.month() + 1); // Months are zero indexed (https://day.js.org/docs/en/get-set/month)
  $("#" + place + "-day").val(d.date());
  $("#" + place + "-year").val(d.year());
  $("#" + place + "-hour").val(d.hour());
  $("#" + place + "-minute").val(d.minute());
  loadDateValues(place);
}

function loadDateValues(place) {
  const month = $("#" + place + "-month").val();
  const day = $("#" + place + "-day").val();
  const year = $("#" + place + "-year").val();
  const hour = $("#" + place + "-hour").val();
  const minute = $("#" + place + "-minute").val();
  const timezone_string = $("#" + place + "-timezone").val();

  const utc = convertDateToMoment(month, day, year, hour, minute);
  if (utc.unix() && month && day && year && hour && minute) {
    $("#" + place).val(utc.unix());
    $("#" + place + "-local").val(
      utc.format("dddd, MMMM Do YYYY, h:mm:ss a z (zzz)"),
    );
    $("#" + place + "-zonetime").val(
      utc.tz(timezone_string).format("dddd, MMMM Do YYYY, h:mm:ss a z (zzz)"),
    );
  } else {
    $("#" + place).val("");
    $("#" + place + "-local").val("");
    $("#" + place + "-zonetime").val("");
  }
}

function convertDateToMoment(month, day, year, hour, minute) {
  let month_num = month.toString();
  if (month_num.length == 1) {
    month_num = "0" + month_num;
  }

  let day_str = day.toString();
  if (day_str.length == 1) {
    day_str = "0" + day_str;
  }

  let hour_str = hour.toString();
  if (hour_str.length == 1) {
    hour_str = "0" + hour_str;
  }

  let min_str = minute.toString();
  if (min_str.length == 1) {
    min_str = "0" + min_str;
  }

  // 2013-02-08 24:00
  const date_string =
    year.toString() +
    "-" +
    month_num +
    "-" +
    day_str +
    " " +
    hour_str +
    ":" +
    min_str +
    ":00";
  return dayjs(date_string);
}

function updateConfigs(event) {
  event.preventDefault();
  const obj = $(this).serializeJSON();
  const params = {};

  if (obj.mail_useauth === false) {
    obj.mail_username = null;
    obj.mail_password = null;
  } else {
    if (obj.mail_username === "") {
      delete obj.mail_username;
    }
    if (obj.mail_password === "") {
      delete obj.mail_password;
    }
  }

  Object.keys(obj).forEach(function (x) {
    if (obj[x] === "true") {
      params[x] = true;
    } else if (obj[x] === "false") {
      params[x] = false;
    } else {
      params[x] = obj[x];
    }
  });

  CTFd.api.patch_config_list({}, params).then(function (_response) {
    if (_response.success) {
      window.location.reload();
    } else {
      let errors = _response.errors.value.join("\n");
      ezAlert({
        title: "Error!",
        body: errors,
        button: "Okay",
      });
    }
  });
}

function uploadLogo(event) {
  event.preventDefault();
  let form = event.target;
  helpers.files.upload(form, {}, function (response) {
    const f = response.data[0];
    const params = {
      value: f.location,
    };
    CTFd.fetch("/api/v1/configs/ctf_logo", {
      method: "PATCH",
      body: JSON.stringify(params),
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (response) {
        if (response.success) {
          window.location.reload();
        } else {
          ezAlert({
            title: "Error!",
            body: "Logo uploading failed!",
            button: "Okay",
          });
        }
      });
  });
}

function switchUserMode(event) {
  event.preventDefault();
  let formData = new FormData(event.target);
  let msg =
    "Are you sure you'd like to switch user modes?\n\nAll submissions, awards, unlocks, and tracking will be deleted!";
  if (formData.get("user_mode") == "users") {
    msg =
      "Are you sure you'd like to switch user modes?\n\nAll teams, submissions, awards, unlocks, and tracking will be deleted!";
  }
  if (confirm(msg)) {
    // Use original form to include original input
    formData.append("submissions", true);
    formData.append("nonce", CTFd.config.csrfNonce);
    fetch(CTFd.config.urlRoot + "/admin/reset", {
      method: "POST",
      credentials: "same-origin",
      body: formData,
    });
    // Bind `this` so that we can reuse the updateConfigs function
    let binded = updateConfigs.bind(this);
    binded(event);
  }
}

function removeLogo() {
  ezQuery({
    title: "Remove logo",
    body: "Are you sure you'd like to remove the CTF logo?",
    success: function () {
      const params = {
        value: null,
      };
      CTFd.api
        .patch_config({ configKey: "ctf_logo" }, params)
        .then((_response) => {
          window.location.reload();
        });
    },
  });
}

function smallIconUpload(event) {
  event.preventDefault();
  let form = event.target;
  helpers.files.upload(form, {}, function (response) {
    const f = response.data[0];
    const params = {
      value: f.location,
    };
    CTFd.fetch("/api/v1/configs/ctf_small_icon", {
      method: "PATCH",
      body: JSON.stringify(params),
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (response) {
        if (response.success) {
          window.location.reload();
        } else {
          ezAlert({
            title: "Error!",
            body: "Icon uploading failed!",
            button: "Okay",
          });
        }
      });
  });
}

function removeSmallIcon() {
  ezQuery({
    title: "Remove logo",
    body: "Are you sure you'd like to remove the small site icon?",
    success: function () {
      const params = {
        value: null,
      };
      CTFd.api
        .patch_config({ configKey: "ctf_small_icon" }, params)
        .then((_response) => {
          window.location.reload();
        });
    },
  });
}

function importCSV(event) {
  event.preventDefault();
  let csv_file = document.getElementById("import-csv-file").files[0];
  let csv_type = document.getElementById("import-csv-type").value;

  let form_data = new FormData();
  form_data.append("csv_file", csv_file);
  form_data.append("csv_type", csv_type);
  form_data.append("nonce", CTFd.config.csrfNonce);

  let pg = ezProgressBar({
    width: 0,
    title: "Upload Progress",
  });

  $.ajax({
    url: CTFd.config.urlRoot + "/admin/import/csv",
    type: "POST",
    data: form_data,
    processData: false,
    contentType: false,
    statusCode: {
      500: function (resp) {
        // Normalize errors
        let errors = JSON.parse(resp.responseText);
        let errorText = "";
        errors.forEach((element) => {
          errorText += `Line ${element[0]}: ${JSON.stringify(element[1])}\n`;
        });

        // Show errors
        alert(errorText);

        // Hide progress modal if its there
        pg = ezProgressBar({
          target: pg,
          width: 100,
        });
        setTimeout(function () {
          pg.modal("hide");
        }, 500);
      },
    },
    xhr: function () {
      let xhr = $.ajaxSettings.xhr();
      xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
          let width = (e.loaded / e.total) * 100;
          pg = ezProgressBar({
            target: pg,
            width: width,
          });
        }
      };
      return xhr;
    },
    success: function (_data) {
      pg = ezProgressBar({
        target: pg,
        width: 100,
      });
      setTimeout(function () {
        pg.modal("hide");
      }, 500);
      setTimeout(function () {
        window.location.reload();
      }, 700);
    },
  });
}

function importConfig(event) {
  event.preventDefault();
  let import_file = document.getElementById("import-file").files[0];

  let form_data = new FormData();
  form_data.append("backup", import_file);
  form_data.append("nonce", CTFd.config.csrfNonce);

  let pg = ezProgressBar({
    width: 0,
    title: "Upload Progress",
  });

  $.ajax({
    url: CTFd.config.urlRoot + "/admin/import",
    type: "POST",
    data: form_data,
    processData: false,
    contentType: false,
    statusCode: {
      500: function (resp) {
        alert(resp.responseText);
      },
    },
    xhr: function () {
      let xhr = $.ajaxSettings.xhr();
      xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
          let width = (e.loaded / e.total) * 100;
          pg = ezProgressBar({
            target: pg,
            width: width,
          });
        }
      };
      return xhr;
    },
    success: function (_data) {
      pg = ezProgressBar({
        target: pg,
        width: 100,
      });
      location.href = CTFd.config.urlRoot + "/admin/import";
    },
  });
}

function exportConfig(event) {
  event.preventDefault();
  window.location.href = $(this).attr("href");
}

function insertTimezones(target) {
  let current = $("<option>").text(dayjs.tz.guess());
  $(target).append(current);
  let tz_names = timezones;
  for (let i = 0; i < tz_names.length; i++) {
    let tz = $("<option>").text(tz_names[i]);
    $(target).append(tz);
  }
}

$(() => {
  const theme_header_editor = CodeMirror.fromTextArea(
    document.getElementById("theme-header"),
    {
      lineNumbers: true,
      lineWrapping: true,
      mode: "htmlmixed",
      htmlMode: true,
    },
  );

  const theme_footer_editor = CodeMirror.fromTextArea(
    document.getElementById("theme-footer"),
    {
      lineNumbers: true,
      lineWrapping: true,
      mode: "htmlmixed",
      htmlMode: true,
    },
  );

  const theme_settings_editor = CodeMirror.fromTextArea(
    document.getElementById("theme-settings"),
    {
      lineNumbers: true,
      lineWrapping: true,
      readOnly: true,
      mode: { name: "javascript", json: true },
    },
  );

  // Handle refreshing codemirror when switching tabs.
  // Better than the autorefresh approach b/c there's no flicker
  $("a[href='#theme']").on("shown.bs.tab", function (_e) {
    theme_header_editor.refresh();
    theme_footer_editor.refresh();
    theme_settings_editor.refresh();
  });

  $(
    "a[href='#legal'], a[href='#tos-config'], a[href='#privacy-policy-config']",
  ).on("shown.bs.tab", function (_e) {
    $("#tos-config .CodeMirror").each(function (i, el) {
      el.CodeMirror.refresh();
    });
    $("#privacy-policy-config .CodeMirror").each(function (i, el) {
      el.CodeMirror.refresh();
    });
  });

  $("#theme-settings-modal form").submit(function (e) {
    e.preventDefault();
    theme_settings_editor
      .getDoc()
      .setValue(JSON.stringify($(this).serializeJSON(), null, 2));
    $("#theme-settings-modal").modal("hide");
  });

  $("#theme-settings-button").click(function () {
    let form = $("#theme-settings-modal form");
    let data;

    // Ignore invalid JSON data
    try {
      data = JSON.parse(theme_settings_editor.getValue());
    } catch (e) {
      data = {};
    }

    $.each(data, function (key, value) {
      var ctrl = form.find(`[name='${key}']`);
      switch (ctrl.prop("type")) {
        case "radio":
        case "checkbox":
          ctrl.each(function () {
            $(this).attr("checked", value);
            $(this).attr("value", value);
          });
          break;
        default:
          ctrl.val(value);
      }
    });
    $("#theme-settings-modal").modal();
  });

  insertTimezones($("#start-timezone"));
  insertTimezones($("#end-timezone"));
  insertTimezones($("#freeze-timezone"));

  $(".config-section > form:not(.form-upload, .custom-config-form)").submit(
    updateConfigs,
  );
  $("#logo-upload").submit(uploadLogo);
  $("#user-mode-form").submit(switchUserMode);
  $("#remove-logo").click(removeLogo);
  $("#ctf-small-icon-upload").submit(smallIconUpload);
  $("#remove-small-icon").click(removeSmallIcon);
  $("#export-button").click(exportConfig);
  $("#import-button").click(importConfig);
  $("#import-csv-form").submit(importCSV);
  $("#config-color-update").click(function () {
    const hex_code = $("#config-color-picker").val();
    const user_css = theme_header_editor.getValue();
    let new_css;
    if (user_css.length) {
      let css_vars = `theme-color: ${hex_code};`;
      new_css = user_css.replace(/theme-color: (.*);/, css_vars);
    } else {
      new_css =
        `<style id="theme-color">\n` +
        `:root {--theme-color: ${hex_code};}\n` +
        `.navbar{background-color: var(--theme-color) !important;}\n` +
        `.jumbotron{background-color: var(--theme-color) !important;}\n` +
        `</style>\n`;
    }
    theme_header_editor.getDoc().setValue(new_css);
  });

  $(".start-date").change(function () {
    loadDateValues("start");
  });
  $(".end-date").change(function () {
    loadDateValues("end");
  });
  $(".freeze-date").change(function () {
    loadDateValues("freeze");
  });

  const start = $("#start").val();
  const end = $("#end").val();
  const freeze = $("#freeze").val();

  if (start) {
    loadTimestamp("start", start);
  }
  if (end) {
    loadTimestamp("end", end);
  }
  if (freeze) {
    loadTimestamp("freeze", freeze);
  }

  // Toggle username and password based on stored value
  $("#mail_useauth")
    .change(function () {
      $("#mail_username_password").toggle(this.checked);
    })
    .change();

  $("#config-sidebar .nav-link").click(function () {
    window.scrollTo(0, 0);
  });

  // Insert FieldList element for users
  const fieldList = Vue.extend(FieldList);
  let userVueContainer = document.createElement("div");
  document.querySelector("#user-field-list").appendChild(userVueContainer);
  new fieldList({
    propsData: {
      type: "user",
    },
  }).$mount(userVueContainer);

  // Insert FieldList element for teams
  let teamVueContainer = document.createElement("div");
  document.querySelector("#team-field-list").appendChild(teamVueContainer);
  new fieldList({
    propsData: {
      type: "team",
    },
  }).$mount(teamVueContainer);

  const bracketList = Vue.extend(BracketList);
  let bracketListContainer = document.createElement("div");
  document.querySelector("#brackets-list").appendChild(bracketListContainer);
  new bracketList({}).$mount(bracketListContainer);

  // --- GitHub Repository Sync Section ---
  const ITEMS_PER_PAGE = 10;
  let allRepos = [];
  let currentPage = 1;

  const githubLoginSection = document.getElementById("github-login-section");
  const githubReposSection = document.getElementById("github-repos-section");
  const githubReposList = document.getElementById("github-repos-list");
  const githubRepoSearch = document.getElementById("github-repo-search");
  const githubRepoPagination = document.getElementById("github-repo-pagination");

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

  githubRepoSearch?.addEventListener("input", () => {
    currentPage = 1;
    renderRepos();
  });

  // Fetch repos from the API
  fetch("/api/v1/github/repos")
    .then(response => {
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("User not authenticated with GitHub. Please install the app or make sure you have the necessary permissions.");
        }
        return response.json().then(err => {
          throw new Error(err.message || "Unexpected error communicating with the API.");
        });
      }
      return response.json();
    })
    .then(data => {
      if (!data.success) {
        throw new Error(data.message || "The API did not respond successfully.");
      }

      allRepos = data.repos || [];

      // Ensure sections are displayed and hidden correctly
      if (githubLoginSection) githubLoginSection.style.display = "none";
      if (githubReposSection) githubReposSection.style.display = "block";
      const errorSection = document.getElementById("github-error-section");
      if (errorSection) errorSection.style.display = "none";

      renderRepos();
      loadSavedRepos();
    })
    .catch(error => {
      console.error("Error fetching the repos:", error);
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

    CTFd.fetch("/api/v1/github/repos/selection", {
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
          ezAlert({
            title: "Success",
            body: "Repositories saved successfully.",
            button: "OK"
          });
        } else {
          ezAlert({
            title: "Error saving",
            body: data.message || "Unexpected error.",
            button: "OK"
          });
        }
      })
      .catch(err => {
        ezAlert({
          title: "Unexpected Error",
          body: err.message,
          button: "OK"
        });
      });
  });

  function loadSavedRepos() {
    const tableBody = document.querySelector("#github-saved-repos-table tbody");
    tableBody.innerHTML = "";

    CTFd.fetch("/api/v1/github/repos/saved", {
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
          lastImportTd.textContent = repo.last_synced_at ? repo.last_synced_at : "-";

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
            ezQuery({
              title: "Delete Repository?",
              body: "Are you sure you want to delete this repository?",
              success: () => {
                CTFd.fetch(`/api/v1/github/repos/${repoId}`, {
                  method: "DELETE",
                  credentials: "same-origin",
                  headers: {
                    "CSRF-Token": CTFd.config.csrfNonce
                  }
                })
                  .then((r) => r.json())
                  .then((resp) => {
                    if (resp.success) {
                      ezAlert({
                        title: "Deleted",
                        body: resp.message,
                        button: "OK"
                      });
                      loadSavedRepos();
                    } else {
                      ezAlert({
                        title: "Error",
                        body: resp.message,
                        button: "Close"
                      });
                    }
                  });
              }
            });
          });
        });

        document.querySelectorAll(".sync-now-btn").forEach((btn) => {
          btn.addEventListener("click", () => {
            const repoId = btn.getAttribute("data-id");

            ezQuery({
              title: "Import Challenges?",
              body: "Are you sure you want to import the challenges from this repository?",
              success: () => {
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

                CTFd.fetch(`/api/v1/github/repos/${repoId}/import`, {
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
                      if (resp.errors && resp.errors.length > 0) {
                        body += "<hr><b>Errors during import:</b><ul>";
                        resp.errors.forEach((err) => {
                          body += `<li><code>${err.file}</code>: ${err.error}</li>`;
                        });
                        body += "</ul>";
                      }

                      ezAlert({
                        title: "Import Complete",
                        body: body,
                        button: "OK"
                      });

                      loadSavedRepos(); // Update the entire table
                    } else {
                      syncCell.innerHTML = originalSyncContent;
                      btn.disabled = false;
                      deleteBtn.disabled = false;

                      ezAlert({
                        title: "Error",
                        body: resp.message,
                        button: "Close"
                      });
                    }
                  })
                  .catch((err) => {
                    syncCell.innerHTML = originalSyncContent;
                    btn.disabled = false;
                    deleteBtn.disabled = false;

                    ezAlert({
                      title: "Unexpected Error",
                      body: err.message,
                      button: "Close"
                    });
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
        });

        document.getElementById("import-selected-repos")?.addEventListener("click", () => {
          const checkboxes = document.querySelectorAll(".sync-checkbox:checked");
          if (checkboxes.length === 0) {
            ezAlert({ title: "No Selection", body: "Select at least one repository to import.", button: "OK" });
            return;
          }

          ezQuery({
            title: "Import Multiple Repositories?",
            body: `You will import ${checkboxes.length} repositories. Continue?`,
            success: () => {
              checkboxes.forEach((cb) => {
                const repoId = cb.value;
                const row = cb.closest("tr");
                importRepoById(repoId, row);
              });
            }
          });
        });
      })
      .catch((err) => {
        ezAlert({
          title: "Error",
          body: err.message,
          button: "OK"
        });
      });
  }

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

    CTFd.fetch(`/api/v1/github/repos/${repoId}/import`, {
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
          ezAlert({ title: "Import Complete", body, button: "OK" });
          loadSavedRepos();
        } else {
          ezAlert({ title: "Error", body: resp.message, button: "Close" });
          syncCell.innerHTML = originalSyncContent;
        }
      })
      .catch((err) => {
        ezAlert({ title: "Unexpected Error", body: err.message, button: "Close" });
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

});
