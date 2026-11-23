
document.addEventListener("DOMContentLoaded", function () {

    const modal = document.getElementById("databaseCredentialsModal");

    const form = document.getElementById("databaseCredentialsForm");

    const connectionName = document.getElementById("databaseConnectionName");

    const sqlCredentials = document.getElementById("sqlCredentials");

    const windowsCredentials = document.getElementById("windowsCredentials");

    const username = document.getElementById("databaseUsername");

    const password = document.getElementById("databasePassword");

    const submitButton = document.getElementById("databaseCredentialsSubmit");


    // Handle selection of a connection to test
    document.querySelectorAll(".database-credentials-btn").forEach(function (button) {

        button.addEventListener("click", function () {

            const actionUrl = this.dataset.actionUrl;

            const name = this.dataset.connectionName;

            const authentication = this.dataset.authentication;

            const operation = this.dataset.operation;

            // Set form action
            form.action = actionUrl;

            // Display selected connection
            connectionName.textContent = name;

            // Reset credentials
            form.reset();

            // Configure authentication fields
            if (authentication === "SQL") {

                sqlCredentials.classList.remove("d-none");
                windowsCredentials.classList.add("d-none");

                username.required = true;
                password.required = true;

            } else {

                sqlCredentials.classList.add("d-none");
                windowsCredentials.classList.remove("d-none");

                username.required = false;
                password.required = false;

            }

            // Configure operation button
            if (operation === "test") {
                submitButton.textContent = "Test Connection";

            } else if (operation === "scan") {
                submitButton.textContent = "Start Scan";
            }

        });

    });


    // Clear credentials when modal closes
    modal.addEventListener("hidden.bs.modal", function () {

        form.reset();

        form.action = "";

        username.required = false;
        password.required = false;

        sqlCredentials.classList.add("d-none");
        windowsCredentials.classList.add("d-none");

        submitButton.textContent = "Continue";

    });

});