// plugins/github_backup/static/js/mi_lista_challenges.js

document.addEventListener("DOMContentLoaded", function () {
    console.log("JS cargado");
    console.log("JS cargado");
  const contenedor = document.getElementById("mi_lista_challenges");
  fetch("/api/v1/ctfd_myplugin/challenges")
    .then((resp) => resp.json())
    .then((data) => {
      if (!Array.isArray(data)) {
        contenedor.innerHTML = "<p>Error: respuesta inesperada.</p>";
        return;
      }

      // Creamos una tabla simple
      let html = `<table class="table table-striped">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Categoría</th>
            <th>Valor</th>
          </tr>
        </thead>
        <tbody>
      `;

      data.forEach((c) => {
        html += `<tr>
          <td>${c.id}</td>
          <td>${c.name}</td>
          <td>${c.category}</td>
          <td>${c.value}</td>
        </tr>`;
      });

      html += `</tbody></table>`;

      contenedor.innerHTML = html;
    })
    .catch((err) => {
      console.error(err);
      contenedor.innerHTML = "<p>No se pudo cargar la lista de challenges.</p>";
    });
});
