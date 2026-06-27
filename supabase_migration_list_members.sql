-- ============================================================
-- Thêm hàm liệt kê thành viên (kèm email) cho chủ ao xem
-- Chạy 1 lần trong Supabase SQL Editor
-- ============================================================

create or replace function public.list_pond_members(p_pond_id uuid)
returns table(user_id uuid, email text)
language plpgsql security definer set search_path = public stable
as $$
begin
  if not public.is_pond_owner(p_pond_id) then
    raise exception 'Chỉ chủ ao mới được xem danh sách thành viên';
  end if;

  return query
    select m.user_id, u.email::text
    from public.pond_members m
    join auth.users u on u.id = m.user_id
    where m.pond_id = p_pond_id;
end;
$$;
