$(function () {
    // Toggle pills on click
    $('.hover-pills-container .toggle-pills').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        var $container = $(this).closest('.hover-pills-container');
        var wasOpen = $container.hasClass('show-pills');
        
        // Close all others
        $('.hover-pills-container').removeClass('show-pills');
        
        // Toggle this one
        if (!wasOpen) {
            $container.addClass('show-pills');
        }
    });

    // Prevent closing when clicking inside the hidden pills
    $('.hover-pills-container .hidden-pills').on('click', function(e) {
        e.stopPropagation();
    });

    // Close all when clicking outside
    $(document).on('click', function(e) {
        if ($(e.target).closest('.hover-pills-container').length === 0) {
            $('.hover-pills-container').removeClass('show-pills');
        }
    });
});
