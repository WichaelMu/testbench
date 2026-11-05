" Run inside the user's kvim/vim, after their usual vimrc has loaded.
let s:state = json_decode(join(readfile(g:invokation_state_path), "\n"))
let s:payload = bufnr('%')
let s:payload_window = win_getid()
let s:timer = -1
let s:busy = 1
let s:exiting = 0
let s:last_text = s:state.text

set encoding=utf-8
set laststatus=2 noshowmode
setlocal buftype=acwrite bufhidden=hide noswapfile noundofile
setlocal filetype=json number relativenumber nowrap
setlocal expandtab shiftwidth=2 softtabstop=2 autoindent
setlocal statusline=%!InvokationStatus()
setlocal nomodified

function! InvokationStatus() abort
    let l:mode = mode() =~# '^[iR]' ? 'INSERT' : (mode() =~# '^[vV\x16]' ? 'VISUAL' : 'NORMAL')
    let l:scope = s:state.global_scope ? 'GLOBAL' : 'LAMBDA'
    let l:source = 'Draft'
    for l:index in range(len(s:state.records))
        if s:state.records[l:index].id ==# s:state.current_id
            let l:source = 'History ' . (l:index + 1)
            break
        endif
    endfor
    return ' ' . l:mode . ' · ' . l:scope . ' · ' . l:source . ' %= %l:%c '
endfunction

function! s:Cursor() abort
    let l:above = line('.') > 1 ? join(getline(1, line('.') - 1), "\n") . "\n" : ''
    return strchars(l:above) + strchars(strpart(getline('.'), 0, col('.') - 1))
endfunction

function! s:SetCursor(offset) abort
    let l:remaining = a:offset
    let l:lines = getline(1, '$')
    for l:index in range(len(l:lines))
        let l:length = strchars(l:lines[l:index])
        if l:remaining <= l:length
            let l:byte = byteidxcomp(l:lines[l:index], l:remaining)
            call cursor(l:index + 1, (l:byte < 0 ? strlen(l:lines[l:index]) : l:byte) + 1)
            return
        endif
        let l:remaining -= l:length + 1
    endfor
    call cursor(line('$'), strlen(getline('$')) + 1)
endfunction

function! s:SetText(text) abort
    let l:lines = split(a:text, "\n", 1)
    call setline(1, empty(l:lines) ? [''] : l:lines)
    if line('$') > max([1, len(l:lines)])
        call deletebufline(s:payload, max([1, len(l:lines)]) + 1, '$')
    endif
endfunction

function! s:Sidebar() abort
    let l:selected = 1
    let l:rows = ['Draft']
    for l:index in range(len(s:state.records))
        call add(l:rows, 'History ' . (l:index + 1))
        if s:state.records[l:index].id ==# s:state.current_id
            let l:selected = l:index + 2
        endif
    endfor
    let l:rows[l:selected - 1] = '› ' . l:rows[l:selected - 1]
    call map(l:rows, 'v:key == l:selected - 1 ? v:val : "  " . v:val')
    call setbufvar(s:sidebar, '&modifiable', 1)
    call setbufline(s:sidebar, 1, l:rows)
    if len(getbufline(s:sidebar, 1, '$')) > len(l:rows)
        call deletebufline(s:sidebar, len(l:rows) + 1, '$')
    endif
    call setbufvar(s:sidebar, '&modifiable', 0)
    call win_execute(s:sidebar_window, 'call cursor(' . l:selected . ', 1) | normal! zv')
    call win_execute(s:sidebar_window, 'call clearmatches() | call matchaddpos("InvokationSelected", [' . l:selected . '])')
    redrawstatus
endfunction

function! InvokationRequest(action, ...) abort
    if s:busy || s:exiting || bufnr('%') != s:payload
        return
    endif
    if s:timer != -1
        call timer_stop(s:timer)
        let s:timer = -1
    endif
    let s:busy = 1
    try
        let l:text = join(getline(1, '$'), "\n")
        let l:cursor = s:Cursor()
        let l:request = {'action': a:action, 'text': l:text, 'cursor': l:cursor, 'count': a:0 ? a:1 : 1}
        call writefile([json_encode(l:request)], fnamemodify(g:invokation_state_path, ':h') . '/request.json')
        " Keep raw terminal input while saving so typeahead is never echoed.
        silent let l:result = system(join(map(copy(g:invokation_bridge), 'shellescape(v:val)'), ' '))
        if v:shell_error
            echohl ErrorMsg
            echomsg 'Could not save JSON draft: ' . l:result
            echohl None
            return
        endif
        let s:state = json_decode(join(readfile(g:invokation_state_path), "\n"))
        if s:state.text !=# l:text
            call s:SetText(s:state.text)
        endif
        if s:state.cursor != l:cursor || s:state.text !=# l:text
            call s:SetCursor(s:state.cursor)
        endif
        let s:last_text = s:state.text
        setlocal nomodified
        call s:Sidebar()
        if !empty(s:state.error)
            echohl ErrorMsg
            echomsg s:state.error
            echohl None
        elseif !empty(s:state.action)
            let s:exiting = 1
            qall!
        endif
    finally
        let s:busy = 0
    endtry
endfunction

function! s:Save(timer) abort
    let s:timer = -1
    if bufnr('%') == s:payload
        call InvokationRequest('save')
    endif
endfunction

function! s:Changed() abort
    if s:busy || s:exiting || bufnr('%') != s:payload
        return
    endif
    " Editing a history entry makes it the draft immediately.
    if join(getline(1, '$'), "\n") !=# s:last_text
        let s:state.current_id = v:null
        call s:Sidebar()
    endif
    if s:timer != -1
        call timer_stop(s:timer)
    endif
    let s:timer = timer_start(250, function('s:Save'))
endfunction

function! s:Leaving() abort
    if !s:exiting && bufexists(s:payload)
        call win_gotoid(s:payload_window)
        call InvokationRequest('save')
    endif
endfunction

" Ctrl+J is the only invoke key binding in the JSON editor.
for s:mode in ['n', 'i', 'x']
    execute s:mode . 'noremap <silent> <buffer> <Up> <Cmd>call InvokationRequest("older", v:count1)<CR>'
    execute s:mode . 'noremap <silent> <buffer> <Down> <Cmd>call InvokationRequest("newer", v:count1)<CR>'
    for [s:key, s:action] in [['<C-J>', 'invoke'], ['<F4>', 'format'], ['<F3>', 'scope'], ['<F2>', 'history'], ['<C-C>', 'cancel']]
        execute s:mode . 'noremap <silent> <buffer> ' . s:key . ' <Cmd>call InvokationRequest("' . s:action . '")<CR>'
    endfor
endfor
" Vim requires custom command names to start with a capital letter. Expand
" :wq[!] only in this buffer's Ex command line, leaving searches untouched.
command! -buffer -bang InvokationWriteQuit call InvokationRequest('invoke')
cnoreabbrev <buffer> <expr> wq getcmdtype() ==# ':' && getcmdline() =~# '^\s*wq$' ? 'InvokationWriteQuit' : 'wq'
command! PayloadHistory call InvokationRequest('history')
command! PayloadScope call InvokationRequest('scope')

augroup GeniusInvokation
    autocmd!
    autocmd TextChanged,TextChangedI,TextChangedP,CursorMoved,CursorMovedI <buffer> call s:Changed()
    autocmd InsertLeave,FocusLost,BufLeave <buffer> call InvokationRequest('save')
    autocmd BufWriteCmd <buffer> call InvokationRequest('save')
    autocmd QuitPre <buffer> call InvokationRequest('cancel')
    autocmd VimLeavePre * call s:Leaving()
augroup END

botright 19vnew
let s:sidebar = bufnr('%')
let s:sidebar_window = win_getid()
setlocal buftype=nofile bufhidden=wipe noswapfile noundofile nobuflisted
setlocal nonumber norelativenumber nowrap winfixwidth nocursorline
setlocal signcolumn=no foldcolumn=0 statusline=\ History
setlocal nomodifiable
highlight InvokationSelected cterm=bold ctermfg=white ctermbg=23 gui=bold guifg=#ffffff guibg=#294959
nnoremap <silent> <buffer> <CR> <Cmd>call win_gotoid(<SID>PayloadWindow())<CR>

function! s:PayloadWindow() abort
    return s:payload_window
endfunction

call win_gotoid(s:payload_window)
" Preserve a draft's trailing newline as an editable empty line.
if join(getline(1, '$'), "\n") !=# s:state.text
    call s:SetText(s:state.text)
endif
setlocal nomodified
call s:SetCursor(s:state.cursor)
call s:Sidebar()
let s:busy = 0
set showtabline=2
let &tabline = ' Genius Invokation · ' . substitute(s:state.target.name, '%', '%%', 'g') . ' %= F2 history · F3 scope · F4 format · Ctrl+J/:wq! invoke · :q! quit '
echomsg 'Esc normal · i insert · h/j/k/l cursor · Up/Down history · Left/Right cursor · Ctrl+C save & quit'
