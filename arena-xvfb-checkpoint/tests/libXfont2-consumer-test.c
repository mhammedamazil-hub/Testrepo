#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <X11/fonts/fontstruct.h>
#include <X11/fonts/libxfont2.h>

int main(void)
{
    FontNamesPtr names = xfont2_make_font_names_record(1);
    xfont2_pattern_cache_ptr cache;
    int private_index;

    if (!names) return 2;
    if (xfont2_add_font_names_name(names, (char *)"fixed", 5) != Successful) return 3;
    if (names->nnames != 1 || names->length[0] != 5 ||
        strncmp(names->names[0], "fixed", 5) != 0) return 4;
    xfont2_free_font_names(names);

    cache = xfont2_make_font_pattern_cache();
    if (!cache) return 5;
    xfont2_empty_font_pattern_cache(cache);
    if (xfont2_find_cached_font_pattern(cache, "fixed", 5) != NULL) return 6;
    xfont2_free_font_pattern_cache(cache);

    private_index = xfont2_allocate_font_private_index();
    if (private_index < 0) return 7;

    printf("installed libXfont2 consumer: PASS (font-names, pattern cache, private index %d)\n", private_index);
    return 0;
}
