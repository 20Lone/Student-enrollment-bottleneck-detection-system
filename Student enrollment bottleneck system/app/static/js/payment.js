// Payment form validation

document.addEventListener('DOMContentLoaded', function() {
    const cardNumber = document.getElementById('card_number');
    const cardExpiry = document.getElementById('card_expiry');
    const cardCvv = document.getElementById('card_cvv');
    const cardStatus = document.getElementById('cardStatus');
    const payBtn = document.getElementById('payBtn');
    const paymentForm = document.getElementById('paymentForm');

    // Format card number with spaces
    cardNumber.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\s/g, '').replace(/\D/g, '');
        let formatted = value.match(/.{1,4}/g);
        e.target.value = formatted ? formatted.join(' ') : value;

        // Clear error as user types
        hideStatus();
    });

    // Format expiry as MM/YY
    cardExpiry.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length >= 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        e.target.value = value;
    });

    // CVV - numbers only
    cardCvv.addEventListener('input', function(e) {
        e.target.value = e.target.value.replace(/\D/g, '');
    });

    // Form submission — validate before sending
    paymentForm.addEventListener('submit', function(e) {
        const cardNum = cardNumber.value.replace(/\s/g, '');
        const cardName = document.getElementById('card_name').value.trim();
        const expiry = cardExpiry.value.trim();
        const cvv = cardCvv.value.trim();

        // Check all fields
        if (!cardNum) {
            e.preventDefault();
            showError('Please enter your card number.');
            return false;
        }

        if (!luhnCheck(cardNum)) {
            e.preventDefault();
            showError('Please enter a valid card number.');
            return false;
        }

        if (!cardName) {
            e.preventDefault();
            showError('Please enter the cardholder name.');
            return false;
        }

        if (!expiry || expiry.length < 5) {
            e.preventDefault();
            showError('Please enter a valid expiry date (MM/YY).');
            return false;
        }

        if (!cvv || cvv.length < 3) {
            e.preventDefault();
            showError('Please enter a valid CVV.');
            return false;
        }

        // All good — show processing state
        payBtn.textContent = 'Processing...';
        payBtn.disabled = true;
    });

    function showError(msg) {
        cardStatus.className = 'card-status invalid';
        cardStatus.textContent = msg;
    }

    function hideStatus() {
        cardStatus.className = 'card-status';
        cardStatus.textContent = '';
    }
});

function luhnCheck(cardNumber) {
    cardNumber = cardNumber.replace(/\s/g, '').replace(/-/g, '');
    if (!/^\d+$/.test(cardNumber)) return false;
    if (cardNumber.length < 13 || cardNumber.length > 19) return false;
    if (cardNumber === '0'.repeat(cardNumber.length)) return false;

    let digits = cardNumber.split('').map(Number).reverse();
    let total = 0;
    for (let i = 0; i < digits.length; i++) {
        let d = digits[i];
        if (i % 2 === 1) {
            d *= 2;
            if (d > 9) d -= 9;
        }
        total += d;
    }
    return total % 10 === 0;
}
