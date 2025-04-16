chrome.action.onClicked.addListener((tab) => {
    // Get the active tab's URL
    const url = tab.url;
  
    // Define your API endpoint
    const apiUrl = "https://learning-api-234439745674.us-central1.run.app/learn";
  
    // Send the URL to the API
    fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url })
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("URL sent successfully to the API:", data);
      })
      .catch((error) => {
        console.error("Error sending URL to API:", error);
      });
  });
  