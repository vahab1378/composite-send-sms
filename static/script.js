// static/script.js
let statusInterval;

// بارگذاری اولیه
document.addEventListener("DOMContentLoaded", function () {
  loadNumbers();
  loadLastMessage(); // بارگذاری آخرین پیام
  updateStatus();
  statusInterval = setInterval(updateStatus, 2000);

  // مدیریت آپلود فایل
  document
    .getElementById("file-input")
    .addEventListener("change", handleFileUpload);

  // شمارش کاراکترهای متن پیام
  const messageText = document.getElementById("message-text");
  if (messageText) {
    messageText.addEventListener("input", updateCharCount);
    updateCharCount(); 
  }
});


function showTab(tabName) {
  
  document.querySelectorAll(".tab-pane").forEach((tab) => {
    tab.classList.remove("active");
  });
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
  });

  // افزودن کلاس active به تب و دکمه انتخاب شده
  document.getElementById(tabName + "-tab").classList.add("active");
  event.currentTarget.classList.add("active");
}

// بارگذاری شماره‌ها
function loadNumbers() {
  fetch("/api/numbers")
    .then((response) => response.json())
    .then((data) => {
      if (data.numbers) {
        document.getElementById("numbers-text").value = data.numbers;
      }
    })
    .catch((error) => {
      console.error("Error loading numbers:", error);
    });
}

// بارگذاری آخرین پیام ذخیره شده
function loadLastMessage() {
  fetch("/api/last-message")
    .then((response) => response.json())
    .then((data) => {
      if (data.message) {
        const messageText = document.getElementById("message-text");
        if (messageText) {
          messageText.value = data.message;
          updateCharCount();
        }
      }
    })
    .catch((error) => {
      console.error("Error loading last message:", error);
    });
}

// به‌روزرسانی شمارش کاراکترها
function updateCharCount() {
  const messageText = document.getElementById("message-text");
  const charCount = document.getElementById("char-count");
  
  if (messageText && charCount) {
    const count = messageText.value.length;
    charCount.textContent = `${count} کاراکتر`;
    
    // تغییر رنگ اگر از حد مجاز بیشتر شد
    if (count > 160) {
      charCount.style.color = "#f44336";
      charCount.innerHTML = `${count} کاراکتر <i class="fas fa-exclamation-triangle"></i>`;
    } else if (count > 140) {
      charCount.style.color = "#ff9800";
    } else {
      charCount.style.color = "#4caf50";
    }
  }
}

// به‌روزرسانی وضعیت
function updateStatus() {
  fetch("/api/status")
    .then((response) => response.json())
    .then((data) => {
      // به‌روزرسانی وضعیت اجرا
      const statusDot = document.getElementById("status-dot");
      const statusText = document.getElementById("status-text");
      const stopBtn = document.getElementById("stop-btn");

      if (data.running) {
        statusDot.className = "status-dot status-running";
        statusText.textContent = "در حال اجرا";
        stopBtn.disabled = false;
      } else {
        statusDot.className = "status-dot status-stopped";
        statusText.textContent = "متوقف";
        stopBtn.disabled = true;
      }

      // به‌روزرسانی آمار
      document.getElementById("sent-count").textContent =
        data.sent_count.toLocaleString();
      document.getElementById("remaining-count").textContent =
        data.remaining_count.toLocaleString();
      document.getElementById("total-sent").textContent =
        data.total_sent.toLocaleString();
      document.getElementById(
        "batch-info"
      ).textContent = `${data.current_batch}/${data.total_batches}`;

      // به‌روزرسانی نوار پیشرفت
      if (data.total_batches > 0) {
        const progress = (data.current_batch / data.total_batches) * 100;
        document.getElementById("progress-fill").style.width = `${progress}%`;
        document.getElementById("progress-text").textContent = `${Math.round(
          progress
        )}%`;
      }

      // به‌روزرسانی لاگ‌ها
      if (data.logs && data.logs.length > 0) {
        const logsList = document.getElementById("logs-list");
        logsList.innerHTML = "";

        data.logs.forEach((log) => {
          const logEntry = document.createElement("div");
          logEntry.className = "log-entry";
          logEntry.textContent = log;
          logsList.appendChild(logEntry);
        });
      }

      // به‌روزرسانی آمار فایل‌ها
      if (data.stats) {
        // می‌توانید آمار بیشتری نمایش دهید
      }
    })
    .catch((error) => {
      console.error("Error updating status:", error);
    });
}

// شروع ارسال
function startSending() {
  const messageText = document.getElementById("message-text");
  if (!messageText || !messageText.value.trim()) {
    alert("لطفاً متن پیامک را وارد کنید");
    showTab('message');
    return;
  }

  const settings = {
    username: document.getElementById("username").value,
    password: document.getElementById("password").value,
    src_address: document.getElementById("src-address").value,
    interval: parseInt(document.getElementById("interval").value),
    batch_size: parseInt(document.getElementById("batch-size").value),
    numbers: document.getElementById("numbers-text").value,
    message: messageText.value  // اضافه کردن متن پیامک
  };

  // اعتبارسنجی
  if (!settings.username || !settings.password || !settings.src_address) {
    alert("لطفاً تمام فیلدهای الزامی را پر کنید");
    return;
  }

  if (!confirm("آیا از شروع ارسال مطمئن هستید؟")) {
    return;
  }

  fetch("/api/start", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  })
    .then((response) => response.json())
    .then((data) => {
      alert(data.message);
      if (data.success) {
        updateStatus();
      }
    })
    .catch((error) => {
      alert("خطا در شروع ارسال: " + error);
    });
}

// توقف ارسال
function stopSending() {
  if (!confirm("آیا از توقف ارسال مطمئن هستید؟")) {
    return;
  }

  fetch("/api/stop", {
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => {
      alert(data.message);
    })
    .catch((error) => {
      alert("خطا در توقف: " + error);
    });
}

// تست اتصال
function testConnection() {
  const messageText = document.getElementById("message-text");
  const settings = {
    username: document.getElementById("username").value,
    password: document.getElementById("password").value,
    src_address: document.getElementById("src-address").value,
    message: messageText ? messageText.value : "تست اتصال"
  };

  if (!settings.username || !settings.password || !settings.src_address) {
    alert("لطفاً فیلدهای اتصال را پر کنید");
    return;
  }

  fetch("/api/test", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert("✅ " + data.message);
      } else {
        alert("❌ " + data.message);
      }
    })
    .catch((error) => {
      alert("خطا در تست اتصال: " + error);
    });
}

// آپلود فایل
function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  fetch("/api/upload", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        document.getElementById(
          "file-info"
        ).textContent = `فایل با ${data.count} شماره آپلود شد`;
        loadNumbers(); // بارگذاری مجدد شماره‌ها
        alert("✅ فایل با موفقیت آپلود شد");
      } else {
        alert("❌ " + data.message);
      }
    })
    .catch((error) => {
      alert("خطا در آپلود فایل: " + error);
    });

  // ریست کردن input
  event.target.value = "";
}

// دانلود فایل
function downloadFile(type) {
  window.open(`/api/download/${type}`, "_blank");
}

// پاک کردن لاگ‌ها
function clearLogs() {
  if (confirm("آیا از پاک کردن تاریخچه مطمئن هستید؟")) {
    const logsList = document.getElementById("logs-list");
    logsList.innerHTML = '<div class="log-entry">لاگ‌ها پاک شدند</div>';
  }
}

// جلوگیری از بسته شدن صفحه هنگام اجرا
window.addEventListener("beforeunload", function (e) {
  // اگر ارسال در حال انجام است، هشدار بده
  if (
    document.getElementById("status-dot").classList.contains("status-running")
  ) {
    e.preventDefault();
    e.returnValue =
      "ارسال در حال انجام است. آیا مطمئن هستید که می‌خواهید صفحه را ترک کنید؟";
  }
});