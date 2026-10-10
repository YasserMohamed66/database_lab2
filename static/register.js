const registerForm = document.getElementById("registerForm");

const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const confirmPasswordInput = document.getElementById("confirmPassword");

const nameError = document.getElementById("nameError");
const emailError = document.getElementById("emailError");
const passwordError = document.getElementById("passwordError");
const confirmPasswordError = document.getElementById("confirmPasswordError");

// Becomes true after the first press on "Create Account".
// From then on, every field is re-checked while the user types.
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

// Each function checks ONE field, shows or clears its message,
// and returns true when the field is valid.

function validateName() {
    if (nameInput.value.trim() === "") {
        showError(nameInput, nameError, "Name is required");
        return false;
    }

    clearError(nameInput, nameError);
    return true;
}

// something@something.something, with no spaces and exactly one "@"
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateEmail() {
    const email = emailInput.value.trim();

    if (email === "") {
        showError(emailInput, emailError, "Email is required");
        return false;
    }

    if (!EMAIL_PATTERN.test(email)) {
        showError(emailInput, emailError, "Enter a valid email address");
        return false;
    }

    clearError(emailInput, emailError);
    return true;
}

function validatePassword() {
    const password = passwordInput.value;

    if (password === "") {
        showError(passwordInput, passwordError, "Password is required");
        return false;
    }

    if (password.length < 8) {
        showError(
            passwordInput,
            passwordError,
            "Password must be at least 8 characters"
        );
        return false;
    }

    // bcrypt only reads the first 72 bytes, so the server refuses longer ones.
    if (password.length > 72) {
        showError(
            passwordInput,
            passwordError,
            "Password is too long (72 bytes at most)"
        );
        return false;
    }

    if (!/[A-Z]/.test(password)) {
        showError(
            passwordInput,
            passwordError,
            "Password must contain an uppercase letter"
        );
        return false;
    }

    if (!/[a-z]/.test(password)) {
        showError(
            passwordInput,
            passwordError,
            "Password must contain a lowercase letter"
        );
        return false;
    }

    // Symbol = anything that is not a letter or a digit
    if (!/[^A-Za-z0-9]/.test(password)) {
        showError(
            passwordInput,
            passwordError,
            "Password must contain a symbol (e.g. ! @ # $)"
        );
        return false;
    }

    clearError(passwordInput, passwordError);
    return true;
}

function validateConfirmPassword() {
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    if (confirmPassword === "") {
        showError(
            confirmPasswordInput,
            confirmPasswordError,
            "Confirm password is required"
        );

        return false;
    }

    if (password !== "" && password !== confirmPassword) {
        showError(
            confirmPasswordInput,
            confirmPasswordError,
            "Passwords do not match"
        );

        return false;
    }

    clearError(confirmPasswordInput, confirmPasswordError);
    return true;
}

// Re-check a field while typing only if the user already pressed
// the button, or the field is showing a message right now
// (for example one that came back from the server).
function shouldRecheck(errorElement) {
    return triedToSubmit || errorElement.classList.contains("visible");
}


registerForm.addEventListener("submit", function (event) {
    triedToSubmit = true;

    // Run ALL checks (not "a && b && c"), so every empty field
    // gets its own message at the same time.
    const checks = [
        { valid: validateName(), input: nameInput },
        { valid: validateEmail(), input: emailInput },
        { valid: validatePassword(), input: passwordInput },
        { valid: validateConfirmPassword(), input: confirmPasswordInput },
    ];

    const firstInvalid = checks.find(function (check) {
        return !check.valid;
    });

    if (firstInvalid) {
        // Something is wrong: do NOT send the form, and put the
        // cursor in the first field that needs fixing.
        event.preventDefault();
        firstInvalid.input.focus();
    }

    // If everything is valid we do nothing here: the browser sends
    // the form to the server (POST /register) as usual.
});


nameInput.addEventListener("input", function () {
    if (shouldRecheck(nameError)) {
        validateName();
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

    // Changing the password can fix (or break) "Passwords do not match".
    if (shouldRecheck(confirmPasswordError) && confirmPasswordInput.value !== "") {
        validateConfirmPassword();
    }
});


confirmPasswordInput.addEventListener("input", function () {
    if (shouldRecheck(confirmPasswordError)) {
        validateConfirmPassword();
    }
});
