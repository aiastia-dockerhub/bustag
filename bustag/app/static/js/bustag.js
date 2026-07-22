$(function () {
    $('.coverimg').on('click', function () {
        $('#imglarge').attr('src', $(this).attr('src'));
        $('#imagemodal').modal('show');
    });

    $('#pagenav').on('change', function () {
        window.location = $(this).val();
    });

    // 调用推荐清理/重新推荐接口的通用函数
    function callRecommendApi(url, $btn, confirmMsg) {
        if (!confirm(confirmMsg)) {
            return;
        }
        var $result = $('#recommend-result');
        var originalText = $btn.text();
        $btn.prop('disabled', true).text('处理中...');
        $result.removeClass('text-danger').addClass('text-muted').text('处理中...');

        $.ajax({
            url: url,
            method: 'POST',
            dataType: 'json'
        }).done(function (data) {
            if (data.success) {
                var msg = '已清理 ' + data.deleted + ' 条旧推荐';
                if (data.total !== undefined) {
                    msg += '，重新推荐 ' + data.recommended + ' / ' + data.total + ' 条';
                }
                if (data.warning) {
                    msg += '（' + data.warning + '）';
                }
                $result.removeClass('text-muted text-danger').addClass('text-success').text(msg);
            } else {
                $result.removeClass('text-muted text-success').addClass('text-danger').text('失败：' + data.error);
            }
        }).fail(function (xhr) {
            var errMsg = xhr.responseText || '请求失败';
            $result.removeClass('text-muted text-success').addClass('text-danger').text('失败：' + errMsg);
        }).always(function () {
            $btn.prop('disabled', false).text(originalText);
        });
    }

    $('#btn-clear-recommend').on('click', function () {
        callRecommendApi('/api/clear-recommend', $(this),
            '确认清理所有系统推荐记录？\n（用户打标数据会保留）');
    });

    $('#btn-re-recommend').on('click', function () {
        callRecommendApi('/api/re-recommend', $(this),
            '确认清理旧推荐并用当前模型重新推荐？\n（用户打标数据会保留）');
    });
});