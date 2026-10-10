const loginForm = document.getElementById("loginForm");

const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");

const emailError = document.getElementById("emailError");
const passwordError = document.getElementById("passwordError");

let triedToSubmit = false;

function showError(input, errorElement, message) {
    errorElement.textContent = message;
    errorElement.classList.add("visible");

    input.setAttribute("aria-invalid", "true");
}

function clearError(input, errorElement) {
    errorElement.textContent = "";
    errorElement.classList.remove("visible");

    input.removeAttribute("aria-invalid");
}

// Login only checks "is it empty?". We do NOT check the email format
// or the password strength here: a wrong value must give the same
// "Invalid email or password" from the server, and old passwords
// may not follow today's rules.

function validateEmail() {
    if (emailInput.value.trim() === "") {
        showError(emailInput, emailError, "Email is required");
        return false;
    }

    clearError(emailInput, emailError);
    return true;
}

function validatePassword() {
    if (passwordInput.value === "") {
        showError(passwordInput, passwordError, "Password is required");
        return false;
    }

    clearError(passwordInput, passwordError);
    return true;
}

function shouldRecheck(errorElement) {
    return triedToSubmit || errorElement.classList.contains("visible");
}


loginForm.addEventListener("submit", function (event) {
    triedToSubmit = true;

    const checks = [
        { valid: validateEmail(), input: emailInput },
        { valid: validatePassword(), input: passwordInput },
    ];

    const firstInvalid = checks.find(function (check) {
        return !check.valid;
    });

    if (firstInvalid) {
        event.preventDefault();
        firstInvalid.input.focus();
    }
});


emailInput.addEventListener("input", function () {
    if (shouldRecheck(emailError)) {
        validateEmail();
    }
});


passwordInput.addEventListener("input", function () {
    if (shouldRecheck(passwordError)) {
        validatePassword();
    }
});
