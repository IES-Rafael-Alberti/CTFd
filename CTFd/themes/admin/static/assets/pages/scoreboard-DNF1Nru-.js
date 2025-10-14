import{$ as n,C as l,A as f}from"./main-DAF0z70z.js";const u={users:(e,t)=>l.api.patch_user_public({userId:e},t),teams:(e,t)=>l.api.patch_team_public({teamId:e},t)};function p(){const e=n(this),t=e.data("account-id"),i=e.data("state");let s;i==="visible"?s=!0:i==="hidden"&&(s=!1);const d={hidden:s};u[l.config.userMode](t,d).then(a=>{a.success&&(s?(e.data("state","hidden"),e.addClass("btn-danger").removeClass("btn-success"),e.text("Hidden")):(e.data("state","visible"),e.addClass("btn-success").removeClass("btn-danger"),e.text("Visible")))})}function h(e,t){const i={hidden:t==="hidden"},s=[];for(let d of e.accounts)s.push(u[l.config.userMode](d,i));for(let d of e.users)s.push(u.users(d,i));Promise.all(s).then(d=>{window.location.reload()})}function m(e){let t=n(".tab-pane.active input[data-account-id]:checked").map(function(){return n(this).data("account-id")}),i=n(".tab-pane.active input[data-user-id]:checked").map(function(){return n(this).data("user-id")}),s={accounts:t,users:i};f({title:"Toggle Visibility",body:n(`
    <form id="scoreboard-bulk-edit">
      <div class="form-group">
        <label>Visibility</label>
        <select name="visibility" data-initial="">
          <option value="">--</option>
          <option value="visible">Visible</option>
          <option value="hidden">Hidden</option>
        </select>
      </div>
    </form>
    `),button:"Submit",success:function(){let a=n("#scoreboard-bulk-edit").serializeJSON(!0).visibility;h(s,a)}})}n(()=>{n(".scoreboard-toggle").click(p),n("#scoreboard-edit-button").click(m)});function g(e,t){const i=l.config.userMode;let s;return t?i==="teams"?s=`/admin/teams/${e}`:s=`/admin/users/${e}`:i==="teams"?s=`/teams/${e}`:s=`/users/${e}`,s}function v(e,t={}){const i=window.location.origin,d={"admin.users_detail":"/admin/users/<user_id>","admin.teams_detail":"/admin/teams/<team_id>"}[e];if(!d)return console.error(`Route not found: ${e}`),"";let a=d;for(const[c,o]of Object.entries(t)){const r=`<${c}>`;a.includes(r)&&(a=a.replace(r,o))}return i+a}function $(e){const t=e.standings,i=e.user_standings,s=e.mode;let d="";if(t.forEach((a,c)=>{const o=g(a.id,!0);d+=`
      <tr data-href="${o}">
        <td class="border-right text-center" data-checkbox>
          <div class="form-check">
            <input type="checkbox" class="form-check-input" value="${a.id}" data-account-id="${a.id}" autocomplete="off">&nbsp;
          </div>
        </td>
        <td class="text-center" width="10%">${c+1}</td>
        <td>
          <a href="${o}">
            ${a.name}
            ${a.oauth_id?'<span class="badge badge-primary">Official</span>':""}
          </a>
        </td>
        <td>${a.score}</td>
        <td>
          ${a.hidden?'<span class="badge badge-danger">hidden</span>':'<span class="badge badge-success">visible</span>'}
        </td>
      </tr>
    `}),n("#standings-table-body").html(d),s==="teams"&&i){let a="";i.forEach((c,o)=>{const r=v("admin.users_detail",{user_id:c.user_id});a+=`
        <tr data-href="${r}">
          <td class="border-right text-center" data-checkbox>
            <div class="form-check">
              <input type="checkbox" class="form-check-input" value="${c.user_id}" autocomplete="off" data-user-id="${c.user_id}">&nbsp;
            </div>
          </td>
          <td class="text-center" width="10%">${o+1}</td>
          <td>
            <a href="${r}">
              ${c.name}
              ${c.oauth_id?'<span class="badge badge-primary">Official</span>':""}
            </a>
          </td>
          <td>${c.score}</td>
          <td>
            ${c.hidden?'<span class="badge badge-danger">hidden</span>':'<span class="badge badge-success">visible</span>'}
          </td>
        </tr>
      `}),n("#user-standings-table-body").html(a)}}async function b(){try{const t=await(await fetch("/api/v1/scoreboard")).json();t.success&&t.data&&$(t.data)}catch(e){console.error("Error fetching scoreboard data:",e)}}n(document).ready(function(){b(),setInterval(b,2e3)});
