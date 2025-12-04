document.getElementById("saveBtn").addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      function: scrapeChat
    });
  });
});

function scrapeChat() {
  // Try to find the main container. In the Logs view, this is often different than the Playground.
  // We will grab the text broadly to ensure we don't miss anything.
  
  let content = "";
  
  // Method 1: Target the specific message bubbles if possible (Playground view)
  const messages = document.querySelectorAll('.text-message-role, .text-token-text-primary');
  
  // Method 2: Fallback for "Logs" view (as seen in your screenshot)
  // The logs view is often just a formatted list. We will try to capture the 'Input' and 'Output' sections.
  if (messages.length === 0) {
    // General scraper for the readable text in the main view
    const mainView = document.querySelector('main') || document.body;
    content = mainView.innerText;
  } else {
    // Structured scraper
    messages.forEach(msg => {
      content += msg.innerText + "\n\n";
    });
  }

  // Create the timestamp for the filename
  const date = new Date();
  const filename = `openai_log_${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}_${date.getHours()}-${date.getMinutes()}.txt`;

  // Create a download link programmatically
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

