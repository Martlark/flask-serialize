$(".index-delete").click(data => {
    const id = $(data.target).data("id");
    $.ajax(`/setting_delete/${id}`, {method: "delete",}
    ).then(() => location.reload()
    ).fail((xhr, textStatus, errorThrown) =>
        alert(`${xhr.responseText}`)
    );

});

$(".sub-setting-delete").click(data => {
    const id = $(data.target).data("id");
    $.ajax(`/sub_setting_delete/${id}`, {method: "delete",}
    ).then(() => location.reload()
    ).fail((xhr, textStatus, errorThrown) =>
        alert(`${xhr.responseText}`)
    );

});


$(".random-value").each((index, item) => {
    $(item).val(Math.random().toString(36).substring(2, 7))
});

