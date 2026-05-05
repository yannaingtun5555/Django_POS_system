const form = document.querySelector("#login-form");
const usernameInput = document.querySelector("#username");
const passwordInput = document.querySelector("#password");
const submitButton = document.querySelector("#submit-button");
const statusBox = document.querySelector("#form-status");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // clear old message
    statusBox.textContent = "";

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    // basic validation
    if (!username || !password) {
        statusBox.textContent = "Username and password are required.";
        return;
    }

    // loading state
    submitButton.disabled = true;
    submitButton.textContent = "Signing in...";

    try {
        const response = await fetch("/api/auth/login/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                username: username,
                password: password,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Invalid credentials");
        }

        // save tokens
        localStorage.setItem("access", data.access);
        localStorage.setItem("refresh", data.refresh);
        localStorage.setItem("user", JSON.stringify(data.user));

        statusBox.textContent = "Login successful. Redirecting...";

        setTimeout(() => {
            window.location.href = "/dashboard/";
        }, 700);

    } catch (error) {
        statusBox.textContent = error.message;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Sign In";
    }
});