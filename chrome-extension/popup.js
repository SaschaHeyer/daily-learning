document.getElementById("sendUrl").addEventListener("click", () => {
    const status = document.getElementById("status");
    status.textContent = "Sending URL to API...";
  
    // Get the current active tab
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      const activeTab = tabs[0];
      const url = activeTab.url;
  
      // Send the URL to the background script
      chrome.runtime.sendMessage({ action: "sendUrlToApi", url }, response => {
        if (response?.success) {
          status.textContent = "✅ URL sent successfully!";
        } else {
          status.textContent = "❌ Failed to send URL.";
          console.error(response?.error || "Unknown error");
        }
      });
    });
  });
  