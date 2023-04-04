const container = document.getElementById('container1');
const xhr = new XMLHttpRequest();

xhr.onload = function() {
  if (xhr.status === 200) {
    container.innerHTML = xhr.responseText;
  }
};

xhr.open('GET', 'content.html');
xhr.send();