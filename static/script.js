document.addEventListener('DOMContentLoaded', () => {
    // Mobile menu toggle
    const toggle = document.getElementById('mobileToggle');
    const navLinks = document.getElementById('navLinks');
    
    if(toggle && navLinks) {
        toggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // Close alerts
    const alertButtons = document.querySelectorAll('.close-alert');
    alertButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.display = 'none';
        });
    });

    // Image upload preview
    const imageInput = document.getElementById('images');
    const previewGrid = document.getElementById('imagePreview');

    if(imageInput && previewGrid) {
        imageInput.addEventListener('change', function() {
            previewGrid.innerHTML = '';
            
            if(this.files) {
                Array.from(this.files).forEach(file => {
                    if(!file.type.startsWith('image/')) return;
                    
                    if(file.size > 5 * 1024 * 1024) {
                        alert(`File ${file.name} is too large. Max size is 5MB.`);
                        this.value = ''; // Clear input
                        previewGrid.innerHTML = '';
                        return;
                    }

                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.classList.add('image-preview-item');
                        previewGrid.appendChild(img);
                    }
                    reader.readAsDataURL(file);
                });
            }
        });
    }
});
