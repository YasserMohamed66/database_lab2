// Delete: ask "are you sure?" before the form is sent.
document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
        if (!window.confirm(form.dataset.confirm)) {
            event.preventDefault();
        }
    });
});


// Add / edit: check the title in the browser (the server checks again).
// The message goes in the first ".error-message" of the same block
// (the add box, or the list item).
function checkTitle(form) {
    const input = form.querySelector("input[name='title']");
    const block = form.closest(".add-box, .todo-item");
    const errorElement = block.querySelector(".error-message");
    const title = input.value.trim();

    let message = "";

    if (title === "") {
        message = "Title is required";
    } else if (title.length > 200) {
        message = "Title is too long (200 characters at most)";
    }

    errorElement.textContent = message;
    errorElement.classList.toggle("visible", message !== "");

    if (message === "") {
        input.removeAttribute("aria-invalid");
    } else {
        input.setAttribute("aria-invalid", "true");
    }

    return { valid: message === "", input: input };
}

document.querySelectorAll("form[data-title-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
        const result = checkTitle(form);

        if (!result.valid) {
            event.preventDefault();
            result.input.focus();
        }
    });

    // Once a message is showing, update it while the user types.
    form.querySelector("input[name='title']").addEventListener("input", function () {
        const block = form.closest(".add-box, .todo-item");

        if (block.querySelector(".error-message").classList.contains("visible")) {
            checkTitle(form);
        }
    });
});
