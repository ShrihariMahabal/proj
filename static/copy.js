let copyTexts = document.querySelectorAll(".invite-text");
let copyBtns = document.querySelectorAll(".cpy-btn");

// invite link copy button
copyBtns.forEach((copyBtn, index) => {
    let copyText = copyTexts[index];
    let copyLink = copyText.querySelector("input");

    copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(copyLink.value)
            .then(() => {
                console.log("Text copied to clipboard successfully!");
                // Update button text to show "Copied"
                copyBtn.innerHTML = `<img src="${copiedUrl}" alt="">`;
                setTimeout(() => {
                    copyBtn.innerHTML = `<img src="${copySvgUrl}" alt="">`;
                }, 2000); // Reset button text after 2 seconds
            })
            .catch((error) => {
                console.error("Error copying text:    ", error);
            });
    });
});

//group page tabs
const tabs = document.querySelectorAll('.tab-btn');
const all_content = document.querySelectorAll('.content');

tabs.forEach((tab, i) => {
    tab.addEventListener('click', (e) => {
        tabs.forEach(tab=>{tab.classList.remove('active')});
        tab.classList.add('active');

        const line = document.querySelector('.line');
        line.style.width = e.target.offsetWidth + "px";
        line.style.left = e.target.offsetLeft + "px";

        all_content.forEach(content=>{content.classList.remove('active')});
        all_content[i].classList.add('active');
    })
})

//add expense form
document.addEventListener("DOMContentLoaded", function () {
    const paidByBtn = document.getElementById("paidByBtn");
    const paidForBtn = document.getElementById("paidForBtn");
    const paidByDropdown = document.getElementById("paidByDropdown");
    const paidForDropdown = document.getElementById("paidForDropdown");

    paidByBtn.addEventListener("click", function () {
        toggleDropdown(paidByDropdown);
    });

    paidForBtn.addEventListener("click", function () {
        toggleDropdown(paidForDropdown);
    });

    document.addEventListener("click", function (event) {
        if (!paidByDropdown.contains(event.target) && event.target !== paidByBtn) {
            paidByDropdown.style.display = "none";
        }

        if (!paidForDropdown.contains(event.target) && event.target !== paidForBtn) {
            paidForDropdown.style.display = "none";
        }
    });

    function toggleDropdown(dropdown) {
        dropdown.style.display = dropdown.style.display === "none" ? "block" : "none";
    }
});