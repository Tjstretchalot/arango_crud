"""This shows a use-case for this library for performing computations on
an underlying set of data which is too big to fit in memory. If ArangoDB
is used it can scale to as much disk space as ArangoDB has available while
still taking advantage of memory caching on the ArangoDB cluster.

This performs an array sort without ever filling more than a certain amount
in this instances memory. The suggested numbers are small so the example
completes quickly but is trivially configurable.
"""
import numpy as np
import time

# suggested real numbers: 524_288, 32_768
NUM_FLOATS_IN_DATA_ARRAY = 1000
NUM_FLOATS_IN_SORTER_MEMORY = 800


def main():
    from arango_crud import env_config

    page_size = NUM_FLOATS_IN_SORTER_MEMORY // 4
    assert page_size * 4 == NUM_FLOATS_IN_SORTER_MEMORY
    num_pages = NUM_FLOATS_IN_DATA_ARRAY // page_size
    assert num_pages * page_size == NUM_FLOATS_IN_DATA_ARRAY

    cfg = env_config()
    cfg.disable_collection_delete = False

    db = cfg.database('arango_crud_examples')
    coll = db.collection('arango_as_working_space')

    db.create_if_not_exists()
    coll.force_delete()
    coll.create_if_not_exists()

    print('Writing random array')
    for i in range(num_pages):
        arr = np.random.randint(10001, size=page_size)
        coll.create_or_overwrite_doc(f'page-{i}', arr.tolist())

    print('Done! Beginning sort')
    started_at = time.time()
    sort(coll, page_size, num_pages)
    total_seconds = time.time() - started_at

    print(f'Sorted {NUM_FLOATS_IN_DATA_ARRAY} numbers in {total_seconds} seconds')
    assert coll.force_delete() is True


def sort(coll, page_size, num_pages):
    print(f'Sorting {num_pages} pages...')
    for i in range(num_pages):
        sort_page(coll, f'page-{i}')

    print('Finished initial page level sort..')
    merge_size = 1
    prev_page_prefix = 'page'
    while merge_size * 2 < num_pages:
        merge_size *= 2
        new_page_prefix = f'page_x{merge_size}'
        print(f'Merging groups of {merge_size}')

        for i in range(0, num_pages, merge_size):
            start_page = i
            end_page = min(i + merge_size, num_pages)
            half_page = i + (merge_size // 2)
            if end_page <= half_page:
                move_page_lists(
                    coll,
                    tuple(f'{prev_page_prefix}-{j}' for j in range(start_page, end_page)),
                    tuple(f'{new_page_prefix}-{j}' for j in range(start_page, end_page))
                )
                continue

            merge_page_lists(
                coll,
                page_size,
                tuple(f'{prev_page_prefix}-{j}' for j in range(start_page, half_page)),
                tuple(f'{prev_page_prefix}-{j}' for j in range(half_page, end_page)),
                tuple(f'{new_page_prefix}-{j}' for j in range(start_page, end_page))
            )
        prev_page_prefix = new_page_prefix

    print('Performing final merge...')
    start_page = 0
    end_page = num_pages
    half_page = merge_size

    merge_page_lists(
        coll,
        page_size,
        tuple(f'{prev_page_prefix}-{j}' for j in range(start_page, half_page)),
        tuple(f'{prev_page_prefix}-{j}' for j in range(half_page, end_page)),
        tuple(f'page-{j}' for j in range(start_page, end_page))
    )


def sort_page(coll, page):
    arr = np.array(coll.read_doc(page))
    arr.sort()
    coll.create_or_overwrite_doc(page, arr.tolist())


def move_page_lists(coll, from_list, to_list):
    for from_page, to_page in zip(from_list, to_list):
        val = coll.read_doc(from_page)
        coll.create_or_overwrite_doc(to_page, val)
        coll.force_delete_doc(from_page)


def merge_page_lists(coll, page_size, page_list_a, page_list_b, page_list_res):
    """Takes two sorted arrays, a and b, and stores a sorted array containing
    both. Array A is split across pages in page_list_a, and array B is split
    across pages in page_list_b. The result is split across pages in
    page_list_res"""
    current_page_idx_in_a = 0
    current_page_a = np.array(coll.read_doc(page_list_a[0]))
    next_idx_within_page_in_a = 0
    current_page_idx_in_b = 0
    current_page_b = np.array(coll.read_doc(page_list_b[0]))
    next_idx_within_page_in_b = 0

    current_page_idx_in_res = 0
    current_res_page = np.zeros(page_size)
    next_idx_within_res_page = 0

    while True:
        if (next_idx_within_page_in_a < page_size
                and (
                    next_idx_within_page_in_b == page_size
                    or current_page_a[next_idx_within_page_in_a]
                    <= current_page_b[next_idx_within_page_in_b]
                )):
            current_res_page[next_idx_within_res_page] = current_page_a[next_idx_within_page_in_a]
            next_idx_within_page_in_a += 1
            next_idx_within_res_page += 1

            if next_idx_within_res_page == page_size:
                coll.create_or_overwrite_doc(
                    page_list_res[current_page_idx_in_res],
                    current_res_page.tolist()
                )
                next_idx_within_res_page = 0
                current_page_idx_in_res += 1

            if next_idx_within_page_in_a == page_size:
                if current_page_idx_in_a + 1 < len(page_list_a):
                    current_page_idx_in_a += 1
                    next_idx_within_page_in_a = 0
                    current_page_a = np.array(coll.read_doc(page_list_a[current_page_idx_in_a]))
                    assert len(current_page_a) == page_size
                elif next_idx_within_page_in_b == page_size:
                    return
        else:
            current_res_page[next_idx_within_res_page] = current_page_b[next_idx_within_page_in_b]
            next_idx_within_page_in_b += 1
            next_idx_within_res_page += 1

            if next_idx_within_res_page == page_size:
                coll.create_or_overwrite_doc(
                    page_list_res[current_page_idx_in_res],
                    current_res_page.tolist()
                )
                next_idx_within_res_page = 0
                current_page_idx_in_res += 1

            if next_idx_within_page_in_b == page_size:
                if current_page_idx_in_b + 1 < len(page_list_b):
                    current_page_idx_in_b += 1
                    next_idx_within_page_in_b = 0
                    current_page_b = np.array(coll.read_doc(page_list_b[current_page_idx_in_b]))
                    assert len(current_page_b) == page_size
                elif next_idx_within_page_in_a == page_size:
                    return
