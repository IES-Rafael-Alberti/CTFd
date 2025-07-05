import Alpine from "alpinejs";
import CTFd from "./index";

window.CTFd = CTFd;
window.Alpine = Alpine;

// Get the last read notification ID from local storage or cookies
let lastId = CTFd.events.counter.read.getLast();

// Fetch new notifications from the server since the last read ID
CTFd.fetch(`/api/v1/notifications?since_id=${lastId}`)
  .then(response => response.json())
  .then(response => {
    const notifications = response.data;
    const read = CTFd.events.counter.read.getAll();

    // Loop through new notifications before marking them as read
    notifications.forEach(n => {
      // Try to find the corresponding notification DOM element by its ID
      const article = document.querySelector(`.notification[data-id="${n.id}"]`);
      if (article) {
        // Find the title element inside the notification
        const title = article.querySelector(".notification__title");

        // Create a "NEW" badge element with the required classes
        const badge = document.createElement("span");
        badge.classList.add("etiqueta", "etiqueta--secundaria", "etiqueta--notificacion");
        badge.textContent = "NUEVA";

        // Append the badge to the title element
        title.appendChild(badge);
      }

      // Add this notification ID to the list of read IDs
      read.push(n.id);
    });

    // Update the list of read notifications in local storage
    CTFd.events.counter.read.setAll(read);

    // Mark all unread notifications as read
    CTFd.events.counter.unread.readAll();

    // Broadcast the updated unread count (should be 0)
    const count = CTFd.events.counter.unread.getAll().length;
    CTFd.events.controller.broadcast("counter", { count });

    // Store the count in the Alpine store for live updates
    Alpine.store("unread_count", count);
  });

// Start Alpine.js
Alpine.start();
