// Client-side JavaScript helpers for School Management System

document.addEventListener('DOMContentLoaded', function () {
    // 1. Tự động tính điểm trung bình môn khi người dùng gõ vào các ô điểm
    const gradeRows = document.querySelectorAll('.grade-row');
    gradeRows.forEach(row => {
        const txInputs = row.querySelectorAll('.grade-tx');
        const gkInput = row.querySelector('.grade-gk');
        const ckInput = row.querySelector('.grade-ck');
        const avgCell = row.querySelector('.grade-cell-avg');

        function recalculate() {
            let txVals = [];
            txInputs.forEach(input => {
                let v = parseFloat(input.value);
                if (!isNaN(v) && v >= 0 && v <= 10) {
                    txVals.push(v);
                }
            });

            let gkVal = gkInput ? parseFloat(gkInput.value) : NaN;
            let ckVal = ckInput ? parseFloat(ckInput.value) : NaN;

            let totalWeight = txVals.length;
            let totalScore = txVals.reduce((a, b) => a + b, 0);

            if (!isNaN(gkVal) && gkVal >= 0 && gkVal <= 10) {
                totalWeight += 2;
                totalScore += gkVal * 2;
            }

            if (!isNaN(ckVal) && ckVal >= 0 && ckVal <= 10) {
                totalWeight += 3;
                totalScore += ckVal * 3;
            }

            if (totalWeight > 0 && avgCell) {
                let avg = (totalScore / totalWeight).toFixed(1);
                avgCell.textContent = avg;
                if (parseFloat(avg) < 5.0) {
                    avgCell.className = 'grade-cell-avg text-danger';
                } else if (parseFloat(avg) >= 8.0) {
                    avgCell.className = 'grade-cell-avg text-success';
                } else {
                    avgCell.className = 'grade-cell-avg text-primary';
                }
            } else if (avgCell) {
                avgCell.textContent = '---';
                avgCell.className = 'grade-cell-avg text-muted';
            }
        }

        row.querySelectorAll('.grade-input').forEach(inp => {
            inp.addEventListener('input', recalculate);
        });
    });

    // 2. Chức năng chọn nhanh "Tất cả có mặt" trong Điểm danh
    const markAllPresentBtn = document.getElementById('btnMarkAllPresent');
    if (markAllPresentBtn) {
        markAllPresentBtn.addEventListener('click', function () {
            document.querySelectorAll('input[type="radio"][value="P"]').forEach(radio => {
                radio.checked = true;
            });
        });
    }

    // 3. Lọc nhanh bảng dữ liệu bằng ô tìm kiếm tức thì
    const instantSearchInput = document.getElementById('instantTableSearch');
    if (instantSearchInput) {
        instantSearchInput.addEventListener('input', function () {
            const query = this.value.toLowerCase().trim();
            const targetTable = document.querySelector('.searchable-table tbody');
            if (!targetTable) return;

            const rows = targetTable.querySelectorAll('tr');
            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});
