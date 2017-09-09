function showmodal() {
    // Show modal for submitting upgrade jobs
    $('#newStagingModal').modal('show');

}

function showCredentialsModal() {
    // Show modal for gathering credentials
    $('#credentials').modal('show');

}
function submitCreds(url) {
    // called when credentials form is submitted
    var form = $(this)
    form.submit()
    $('#newStagingModal').modal('hide')
    //showProgress(form, url)
}

function confirmDeleteJob() {
    // Show modal for gathering credentials
    $('#confirmDelete').modal('show');

}

function deleteJob(id) {
    $.ajax({
        url: '/api/upgrade/' + id,
        method: 'DELETE'
    })

  .done(function( data ) {
    console.log(data);
      if (data.status == 'deleted') {
        window.location.replace("/upgrade");
      }
      else {
          alert("Couldn't delete job!")
      }


  });
}

jQuery(document).ready(function($) {
    $(".clickable-row").click(function() {
        window.location = $(this).data("href");
    });
});