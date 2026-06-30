/* =========================================================
   ATTENDANCE MS — ADMIN JS (CLEAN VERSION)
   ========================================================= */


/* ================= APPROVE USER ================= */
function approveUser(userId, btn) {
    fetch(`/admin/api/approve/${userId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const card = btn.closest(".user-card");

            card.style.transition = "0.3s ease";
            card.style.opacity = "0";
            card.style.transform = "translateX(20px)";

            setTimeout(() => card.remove(), 300);
        } else {
            alert("Approval failed");
        }
    })
    .catch(err => console.error(err));
}


/* ================= REJECT USER ================= */
function rejectUser(userId, btn) {
    fetch(`/admin/api/reject/${userId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const card = btn.closest(".user-card");

            card.style.transition = "0.3s ease";
            card.style.opacity = "0";
            card.style.transform = "translateX(-20px)";

            setTimeout(() => card.remove(), 300);
        } else {
            alert("Delete failed");
        }
    })
    .catch(err => console.error(err));
}


/* ================= ASSIGN CLASS ================= */
function assignClass(userId, select) {

    fetch(`/admin/api/assign-class/${userId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            class_id: select.value
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            select.style.border = "2px solid #2ea8ff";

            setTimeout(() => {
                select.style.border = "";
            }, 800);
        } else {
            alert("Assignment failed");
        }
    })
    .catch(err => console.error(err));
}