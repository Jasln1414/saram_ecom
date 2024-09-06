// $('.cart_btn').on('click', function(e){
//     e.preventDefault(); 
//     var _qty = $('.quantity').val();
//     var _product_id = $('.prod_id').val();
//     var token = $('input[name=csrfmiddlewaretoken]').val();

//     $.ajax({
//         method : 'POST',
//         url : '/add_to_cart',
//         data : {
//             'quantity' : _qty,
//             'product_id' : _product_id,
//             'csrfmiddlewaretoken': '{{ csrf_token }}'
//         },
//         dataType : 'json',
//         success: function (response) {
//             console.log(response)
//         }
//     });
// });

    function increaseValue() {
        var value = parseInt(document.getElementById('number').value, 10);
        value = isNaN(value) ? 0 : value;
        if (value < 9) {
            value++;
            document.getElementById('number').value = value;
        }
    }

    function decreaseValue() {
        var value = parseInt(document.getElementById('number').value, 10);
        value = isNaN(value) ? 0 : value;
        if (value > 0) {
            value--;
            document.getElementById('number').value = value;
        }
    }
