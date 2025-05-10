import{$ as e,u as c,C as o,A as d}from"./main-sbGV3kXM.js";function h(i){let t=e("input[data-challenge-id]:checked").map(function(){return e(this).data("challenge-id")}),a=t.length===1?"challenge":"challenges";c({title:"Delete Challenges",body:`Are you sure you want to delete ${t.length} ${a}?`,success:function(){const l=[];for(var n of t)l.push(o.fetch(`/api/v1/challenges/${n}`,{method:"DELETE"}));Promise.all(l).then(s=>{window.location.reload()})}})}function u(i){let t=e("input[data-challenge-id]:checked").map(function(){return e(this).data("challenge-id")}),a=t.length===1?"challenge":"challenges";c({title:"Add Challenges to the competition",body:`Are you sure you want to add ${t.length} ${a} to the competition?`,success:function(){const l=[];for(var n of t)l.push(o.fetch(`/api/v1/challenges/${n}/add_to_competition`,{method:"POST"}));Promise.all(l).then(s=>{window.location.reload()})}})}function r(i){let t=e("input[data-challenge-id]:checked").map(function(){return e(this).data("challenge-id")});d({title:"Edit Challenges",body:e(`
    <form id="challenges-bulk-edit">
      <div class="form-group">
        <label>Category</label>
        <input type="text" name="category" data-initial="" value="">
      </div>
      <div class="form-group">
        <label>Value</label>
        <input type="number" name="value" data-initial="" value="">
      </div>
      <div class="form-group">
        <label>State</label>
        <select name="state" data-initial="">
          <option value="">--</option>
          <option value="visible">Visible</option>
          <option value="hidden">Hidden</option>
        </select>
      </div>
    </form>
    `),button:"Submit",success:function(){let a=e("#challenges-bulk-edit").serializeJSON(!0);const l=[];for(var n of t)l.push(o.fetch(`/api/v1/challenges/${n}`,{method:"PATCH",body:JSON.stringify(a)}));Promise.all(l).then(s=>{window.location.reload()})}})}e(()=>{e("#challenges-delete-button").click(h),e("#challenges-edit-button").click(r),e("#challenges-add-to-competition-button").click(u)});
