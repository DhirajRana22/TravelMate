// TravelMate Main JavaScript

$(document).ready(function() {
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Smooth scrolling for anchor links
    $('a[href*="#"]:not([href="#"])').click(function() {
        if (location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '') && location.hostname == this.hostname) {
            var target = $(this.hash);
            target = target.length ? target : $('[name=' + this.hash.slice(1) + ']');
            if (target.length) {
                $('html, body').animate({
                    scrollTop: target.offset().top - 100
                }, 1000);
                return false;
            }
        }
    });

    // Auto-hide alerts after 5 seconds
    $('.alert').each(function() {
        var alert = $(this);
        setTimeout(function() {
            alert.fadeOut('slow');
        }, 5000);
    });

    // Form validation enhancement
    $('form').on('submit', function() {
        var form = $(this);
        var submitBtn = form.find('button[type="submit"]');
        
        // Add loading state to submit button
        if (submitBtn.length) {
            var originalText = submitBtn.html();
            submitBtn.html('<span class="loading-spinner me-2"></span>Processing...');
            submitBtn.prop('disabled', true);
            
            // Re-enable button after 10 seconds (fallback)
            setTimeout(function() {
                submitBtn.html(originalText);
                submitBtn.prop('disabled', false);
            }, 10000);
        }
    });

    // Number input formatting
    $('input[type="tel"], input[name*="phone"]').on('input', function() {
        var value = $(this).val().replace(/\D/g, '');
        if (value.length <= 10) {
            $(this).val(value);
        }
    });

    // Date input minimum date (today) - exclude date of birth fields
    $('input[type="date"]').each(function() {
        var today = new Date().toISOString().split('T')[0];
        var fieldName = $(this).attr('name') || '';
        var fieldId = $(this).attr('id') || '';
        
        // Debug logging
        console.log('Processing date field:', fieldName, fieldId);
        
        // Don't set minimum date for date of birth fields
        var isBirthField = fieldName.includes('date_of_birth') || 
                          fieldId.includes('date_of_birth') ||
                          fieldName.includes('birth') || 
                          fieldId.includes('birth');
        
        if (!$(this).attr('min') && !isBirthField) {
            console.log('Setting min date for:', fieldName || fieldId);
            $(this).attr('min', today);
        } else if (isBirthField) {
            console.log('Skipping birth field:', fieldName || fieldId);
            // Explicitly remove any min attribute that might be set
            $(this).removeAttr('min');
        }
    });

    // Copy to clipboard functionality
    $('.copy-btn').click(function() {
        var target = $(this).data('target');
        var text = $(target).text() || $(target).val();
        
        navigator.clipboard.writeText(text).then(function() {
            // Show success message
            var btn = $('.copy-btn');
            var originalText = btn.html();
            btn.html('<i class="fas fa-check"></i> Copied!');
            
            setTimeout(function() {
                btn.html(originalText);
            }, 2000);
        }).catch(function() {
            // Fallback for older browsers
            var textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            alert('Copied to clipboard!');
        });
    });

    // Seat selection functionality
    $('.seat.available').click(function() {
        var seat = $(this);
        var seatNumber = seat.data('seat');
        var maxSeats = parseInt($('#max-seats').val()) || 4;
        var selectedSeats = $('.seat.selected').length;
        
        if (seat.hasClass('selected')) {
            // Deselect seat
            seat.removeClass('selected');
            updateSelectedSeats();
        } else if (selectedSeats < maxSeats) {
            // Select seat
            seat.addClass('selected');
            updateSelectedSeats();
        } else {
            alert('You can select maximum ' + maxSeats + ' seats.');
        }
    });

    function updateSelectedSeats() {
        var selectedSeats = [];
        $('.seat.selected').each(function() {
            selectedSeats.push($(this).data('seat'));
        });
        
        $('#selected-seats').val(selectedSeats.join(','));
        $('#selected-seats-display').text(selectedSeats.join(', ') || 'None');
        $('#seat-count').text(selectedSeats.length);
        
        // Update total price
        var seatPrice = parseFloat($('#seat-price').val()) || 0;
        var totalPrice = selectedSeats.length * seatPrice;
        $('#total-price').text('रू ' + totalPrice.toFixed(2));
        
        // Enable/disable continue button
        $('#continue-btn').prop('disabled', selectedSeats.length === 0);
    }

    // Payment method selection
    $('.payment-method').click(function() {
        $('.payment-method').removeClass('selected');
        $(this).addClass('selected');
        
        var method = $(this).data('method');
        $('#payment-method').val(method);
        
        // Show/hide payment details based on method
        $('.payment-details').hide();
        $('#' + method + '-details').show();
    });

    // Search suggestions
    function showSearchSuggestions(input, suggestions, data) {
        var value = input.val().toLowerCase();
        if (value.length < 2) {
            suggestions.hide();
            return;
        }
        
        var matches = data.filter(function(item) {
            return item.toLowerCase().includes(value);
        }).slice(0, 5);
        
        if (matches.length > 0) {
            var html = matches.map(function(item) {
                return '<div class="suggestion-item" data-value="' + item + '">' + item + '</div>';
            }).join('');
            suggestions.html(html).show();
        } else {
            suggestions.hide();
        }
    }

    // Handle suggestion clicks
    $(document).on('click', '.suggestion-item', function() {
        var value = $(this).data('value');
        var input = $(this).closest('.position-relative').find('input');
        input.val(value);
        $(this).parent().hide();
    });

    // Hide suggestions when clicking outside
    $(document).click(function(e) {
        if (!$(e.target).closest('.position-relative').length) {
            $('.location-suggestions').hide();
        }
    });

    // Auto-refresh for pending payments/bookings
    if ($('.auto-refresh').length) {
        var refreshInterval = parseInt($('.auto-refresh').data('interval')) || 30000;
        setInterval(function() {
            location.reload();
        }, refreshInterval);
    }

    // Countdown timer
    $('.countdown').each(function() {
        var element = $(this);
        var endTime = new Date(element.data('end-time')).getTime();
        
        var timer = setInterval(function() {
            var now = new Date().getTime();
            var distance = endTime - now;
            
            if (distance < 0) {
                clearInterval(timer);
                element.html('EXPIRED');
                return;
            }
            
            var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            element.html(minutes + 'm ' + seconds + 's');
        }, 1000);
    });

    // Print functionality
    $('.print-btn').click(function() {
        window.print();
    });

    // Back to top button
    $(window).scroll(function() {
        if ($(this).scrollTop() > 100) {
            $('#back-to-top').fadeIn();
        } else {
            $('#back-to-top').fadeOut();
        }
    });

    $('#back-to-top').click(function() {
        $('html, body').animate({scrollTop: 0}, 800);
        return false;
    });

    // Animate elements on scroll
    function animateOnScroll() {
        $('.fade-in, .slide-up').each(function() {
            var element = $(this);
            var elementTop = element.offset().top;
            var elementBottom = elementTop + element.outerHeight();
            var viewportTop = $(window).scrollTop();
            var viewportBottom = viewportTop + $(window).height();
            
            if (elementBottom > viewportTop && elementTop < viewportBottom) {
                element.addClass('animated');
            }
        });
    }

    $(window).scroll(animateOnScroll);
    animateOnScroll(); // Run on page load

    // Initialize any charts or graphs
    if (typeof Chart !== 'undefined') {
        // Chart.js initialization would go here
    }

    // Password strength indicator
    $('input[type="password"]').on('input', function() {
        var password = $(this).val();
        var strength = 0;
        var indicator = $(this).siblings('.password-strength');
        
        if (password.length >= 8) strength++;
        if (password.match(/[a-z]/)) strength++;
        if (password.match(/[A-Z]/)) strength++;
        if (password.match(/[0-9]/)) strength++;
        if (password.match(/[^a-zA-Z0-9]/)) strength++;
        
        var strengthText = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
        var strengthClass = ['danger', 'warning', 'info', 'primary', 'success'];
        
        if (indicator.length && password.length > 0) {
            indicator.removeClass('text-danger text-warning text-info text-primary text-success');
            indicator.addClass('text-' + strengthClass[strength - 1]);
            indicator.text(strengthText[strength - 1] || 'Very Weak');
        }
    });

    // Toggle password visibility
    $('.toggle-password').click(function() {
        var input = $($(this).data('target'));
        var icon = $(this).find('i');
        
        if (input.attr('type') === 'password') {
            input.attr('type', 'text');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            input.attr('type', 'password');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });

    // File upload preview
    $('input[type="file"]').change(function() {
        var input = this;
        var preview = $(input).siblings('.file-preview');
        
        if (input.files && input.files[0]) {
            var reader = new FileReader();
            
            reader.onload = function(e) {
                if (input.files[0].type.startsWith('image/')) {
                    preview.html('<img src="' + e.target.result + '" class="img-thumbnail" style="max-width: 200px;">');
                } else {
                    preview.html('<p>File selected: ' + input.files[0].name + '</p>');
                }
            };
            
            reader.readAsDataURL(input.files[0]);
        }
    });

    console.log('TravelMate JavaScript initialized successfully!');
});

// Global functions
function showNotification(message, type = 'info') {
    var alertClass = 'alert-' + type;
    var alert = $('<div class="alert ' + alertClass + ' alert-dismissible fade show position-fixed" style="top: 20px; right: 20px; z-index: 9999;">' +
                  message +
                  '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                  '</div>');
    
    $('body').append(alert);
    
    setTimeout(function() {
        alert.fadeOut('slow', function() {
            $(this).remove();
        });
    }, 5000);
}

function formatCurrency(amount) {
    return 'रू ' + parseFloat(amount).toFixed(2);
}

function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatTime(time) {
    return new Date('1970-01-01T' + time + 'Z').toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

// Bootstrap navbar is handled automatically, no custom JavaScript needed