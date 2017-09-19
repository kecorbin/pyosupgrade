
// this code sucks
var table = $('#upgrades').DataTable( {
    "ajax": {
            "type" : "GET",
            "url" : "/api/upgrade",
            "dataSrc": function ( json ) {
                return json;
            }
            },
    "columns": [
            { "data": "id" },
            { "data": "mop" },
            { "data": "username" },
            { "data": "device" },
            { "data": "status"},
            { "data": "status",
              "render": function(data,type,row,meta) {
                    if (row.status.includes("FAILED")) {
                        kls = 'danger'
                        value = '100'
                    } else if (row.status.includes("TRANFERRING")) {
                        kls = "success active"
                        value = "25"
                    } else if (row.status.includes("SYNCHRONIZING")) {
                        kls = "success active"
                        value = "40"
                    } else if (row.status.includes("CODE STAGING SUCCESSFUL")) {
                        kls = "info"
                        value = "50"
                    } else if (row.status.includes("BACKING UP RUNNING")) {
                        kls = "success active"
                        value = "55"
                    } else if (row.status.includes("SETTING BOOT VAR")) {
                        kls = "success active"
                        value = "60"
                    } else if (row.status.includes("VERIFY BOOT VAR")) {
                        kls = "success active"
                        value = "65"
                    } else if (row.status.includes("RELOADING")) {
                        kls = "success active"
                        value = "75"
                    } else if (row.status.includes("BACK ONLINE")) {
                        kls = "success active"
                        value = "80"
                    } else if (row.status.includes("VERIFYING")) {
                        kls = "success active"
                        value = "90"
                    } else if (row.status.includes("UPGRADE SUCCESS")) {
                        kls = "success"
                        value = "100"
                    } else if (row.status.includes("Completed")) {
                        kls = "success"
                        value = "100"
                    }

                    var bar = '<div class="progress-bar progress-bar-' + kls + ' progress-bar-striped" role="progressbar" aria-valuenow="' + value + '" aria-valuemin="0" aria-valuemax="' + value + '" style="width:' + value + '%"> ' + value + '% </div>'
                    return bar;
               }
            }
        ]
    } );

// this magic makes the rows clickable
$('.dataTable').on('click', 'tbody tr', function() {
    var url = location.href
  var id = table.row(this).data().id
    window.location.href = "/upgrade/" + id

})

// auto refresh the datatable
setInterval( function () {
    table.ajax.reload();
}, 10000 );

