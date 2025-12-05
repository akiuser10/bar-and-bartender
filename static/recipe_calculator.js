// Real-time cost calculation for recipe creation
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('recipeForm');
    if (!form) return;

    // Store ingredient costs (would ideally come from server, but for now we'll calculate on the fly)
    const ingredientCosts = {};
    
    // Extract costs from labels (simple parsing)
    function extractCostFromLabel(label) {
        const match = label.textContent.match(/AED ([\d.]+)/);
        return match ? parseFloat(match[1]) : 0;
    }
    
    // Initialize ingredient costs
    document.querySelectorAll('label[for^="prod_check_"]').forEach(label => {
        const id = label.getAttribute('for').replace('prod_check_', '');
        const cost = extractCostFromLabel(label);
        ingredientCosts[`prod_${id}`] = cost;
    });
    
    document.querySelectorAll('label[for^="sec_check_"]').forEach(label => {
        const id = label.getAttribute('for').replace('sec_check_', '');
        const cost = extractCostFromLabel(label);
        ingredientCosts[`sec_${id}`] = cost;
    });
    
    document.querySelectorAll('label[for^="rec_check_"]').forEach(label => {
        const id = label.getAttribute('for').replace('rec_check_', '');
        const cost = extractCostFromLabel(label);
        ingredientCosts[`rec_${id}`] = cost;
    });

    function calculateTotalCost() {
        let total = 0;
        
        // Calculate product costs
        document.querySelectorAll('input[name^="prod_"]').forEach(input => {
            if (input.type === 'number' && input.value) {
                const id = input.name.replace('prod_', '');
                const qty = parseFloat(input.value) || 0;
                const cost = ingredientCosts[`prod_${id}`] || 0;
                total += cost * qty;
            }
        });
        
        // Calculate secondary ingredient costs
        document.querySelectorAll('input[name^="sec_"]').forEach(input => {
            if (input.type === 'number' && input.value) {
                const id = input.name.replace('sec_', '');
                const qty = parseFloat(input.value) || 0;
                const cost = ingredientCosts[`sec_${id}`] || 0;
                total += cost * qty;
            }
        });
        
        // Calculate recipe costs
        document.querySelectorAll('input[name^="rec_"]').forEach(input => {
            if (input.type === 'number' && input.value) {
                const id = input.name.replace('rec_', '');
                const qty = parseFloat(input.value) || 0;
                const cost = ingredientCosts[`rec_${id}`] || 0;
                total += cost * qty;
            }
        });
        
        document.getElementById('totalCost').textContent = 'AED ' + total.toFixed(2);
    }

    // Add event listeners to all quantity inputs
    form.addEventListener('input', function(e) {
        if (e.target.type === 'number' && (e.target.name.startsWith('prod_') || 
            e.target.name.startsWith('sec_') || e.target.name.startsWith('rec_'))) {
            calculateTotalCost();
        }
    });

    // Initial calculation
    calculateTotalCost();
});

function toggleProduct(id) {
    const qtyDiv = document.getElementById('prod_qty_' + id);
    const checkbox = document.getElementById('prod_check_' + id);
    if (qtyDiv) {
        qtyDiv.style.display = checkbox.checked ? 'block' : 'none';
        if (!checkbox.checked) {
            const input = qtyDiv.querySelector('input[type="number"]');
            if (input) input.value = '0';
        }
    }
}

function toggleSecondary(id) {
    const qtyDiv = document.getElementById('sec_qty_' + id);
    const checkbox = document.getElementById('sec_check_' + id);
    if (qtyDiv) {
        qtyDiv.style.display = checkbox.checked ? 'block' : 'none';
        if (!checkbox.checked) {
            const input = qtyDiv.querySelector('input[type="number"]');
            if (input) input.value = '0';
        }
    }
}

function toggleRecipe(id) {
    const qtyDiv = document.getElementById('rec_qty_' + id);
    const checkbox = document.getElementById('rec_check_' + id);
    if (qtyDiv) {
        qtyDiv.style.display = checkbox.checked ? 'block' : 'none';
        if (!checkbox.checked) {
            const input = qtyDiv.querySelector('input[type="number"]');
            if (input) input.value = '0';
        }
    }
}

