document.getElementById('codeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const codeInput = document.getElementById('codeInput').value;
    console.log("CODEINPUT: ",codeInput);
    const responseDiv = document.getElementById('response');
    const response = await fetch('/submit_code/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify({code: codeInput})
    });
    const result = await response.json();
    if (result.status === 'success') {
        responseDiv.innerHTML = `<p class="text-success">Correct! Points awarded: ${result.points}<br> Output: "${result.output_code}"</p>`;
    } else {
        responseDiv.innerHTML = `<p class="text-danger">Output: "${result.output_code}"<br>Incorrect! Please try again.</p>`;
    }
});





var editor = ace.edit("editor");
editor.setTheme("ace/theme/monokai");
editor.getSession().setMode("ace/mode/swift");
// editor.getSession().setValue('print("Hello, World!")');

// Update textarea with editor content on form submit
document.getElementById("codeForm").addEventListener("submit", function() {
    document.getElementById("codeInput").value = editor.getSession().getValue();
});