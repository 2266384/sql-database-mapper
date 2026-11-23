
document.addEventListener("DOMContentLoaded", function () { 
    const flashMessages = document.querySelectorAll(".alert-dismissible");

    flashMessages.forEach(function (message) {
        setTimeout(function() {

            /* Fade the alert out */
            // Start fade out
            message.classList.remove("show");

            // Remove the alert after the transition
            setTimeout(function () {
                message.remove();
            }, 500);

            /* Close the alert immediately after the timer has expired */
            /*
            const alert = bootstrap.Alert.getOrCreateInstance(message);
            alert.close();
            */
        }, 3000); // Close time
    });

});
