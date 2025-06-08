import{$ as e,u as s,C as a,A as d}from"./main-DAF0z70z.js";function h(i){let t=e("input[data-challenge-id]:checked").map(function(){return e(this).data("challenge-id")}),n=t.length===1?"challenge":"challenges";s({title:"Delete Challenges",body:`Are you sure you want to delete ${t.length} ${n}?`,success:function(){const l=[];for(var o of t)l.push(a.fetch(`/api/v1/challenges/${o}`,{method:"DELETE"}));Promise.all(l).then(c=>{window.location.reload()})}})}function r(i){let t=e("input[data-challenge-id]:checked").map(function(){return e(this).data("challenge-id")});d({title:"Edit Challenges",body:e(`
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
    `),button:"Submit",success:function(){let n=e("#challenges-bulk-edit").serializeJSON(!0);const l=[];for(var o of t)l.push(a.fetch(`/api/v1/challenges/${o}`,{method:"PATCH",body:JSON.stringify(n)}));Promise.all(l).then(c=>{window.location.reload()})}})}function u(i){let t=e("input[data-challenge-id]:checked").map(function(){return e(this).data("challenge-id")}),n=t.length===1?"challenge":"challenges";s({title:"Add Challenges to the competition",body:`Are you sure you want to add ${t.length} ${n} to the competition?`,success:function(){const l=[];for(var o of t)l.push(a.fetch(`/api/v1/challenges/${o}/add_to_competition`,{method:"POST"}));Promise.all(l).then(c=>{window.location.reload()})}})}function g(i){let t=e("input[data-challenge-id]:checked").map(function(){return e(this).data("challenge-id")}),n=t.length===1?"challenge":"challenges";s({title:"Remove Challenges from the competition",body:`Are you sure you want to remove ${t.length} ${n} from the competition?`,success:function(){const l=[];for(var o of t)l.push(a.fetch(`/api/v1/challenges/${o}/remove_from_competition`,{method:"DELETE"}));Promise.all(l).then(c=>{window.location.reload()})}})}e(()=>{e("#challenges-delete-button").click(h),e("#challenges-edit-button").click(r),e("#challenges-add-to-competition-button").click(u),e("#challenges-remove-from-competition-button").click(g)});
