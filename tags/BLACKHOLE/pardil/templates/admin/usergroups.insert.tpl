#include $site_path + "templates/header.tpl"
<div id="content">
  <h2>Kullanıcı Grupları</h2>
    <p>
      $user isimli kullanıcı $group grubuna eklendi.
    </p>
    <ul>
      <li><a href="admin_usergroups.py?start=$pag_now">Listeye Dön</a></li>
    </ul>
</div>
#include $site_path + "templates/footer.tpl"
